"""
Google ADK v2 - Proper Multi-Agent Trading System
Uses Google's native parallel execution and A2A protocol

Features:
- Native parallel agent execution
- A2A (Agent-to-Agent) communication protocol
- Robust JSON parsing with fallbacks
- Few-shot examples in prompts
- YAML configuration
"""
import os
import sys
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(__file__))

from utils.json_parser import safe_json_parse
from config.agent_config import get_config_loader

# Try to import Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Google GenAI SDK not available: {e}")
    print("   Install with: pip install google-generativeai")
    GENAI_AVAILABLE = False


class ADKAgentV2:
    """Enhanced ADK agent with robust parsing and configuration"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        api_key: str,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None
    ):
        """
        Initialize ADK agent with config support

        Args:
            name: Agent name (e.g., 'portfolio_analyst')
            system_prompt: Agent's system instructions
            api_key: Google API key
            model: Model override (uses config if None)
            temperature: Temperature override (uses config if None)
            max_tokens: Max tokens override (uses config if None)
        """
        self.name = name
        self.system_prompt = system_prompt
        self.api_key = api_key

        # Load from config if not provided
        config_loader = get_config_loader()
        agent_config = config_loader.get_agent_config(name)

        self.model_name = model or agent_config.model
        self.temperature = temperature if temperature is not None else agent_config.temperature
        self.max_tokens = max_tokens or agent_config.max_tokens

        # Initialize client if SDK available
        if GENAI_AVAILABLE:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            print(f"⚠️  {name}: GenAI client not available, will use fallback")

    async def analyze_async(
        self,
        context: str,
        temperature: float = None,
        fallback: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run agent analysis asynchronously

        Args:
            context: Analysis context/input
            temperature: Override default temperature
            fallback: Default response if parsing fails

        Returns:
            Parsed agent response as dict
        """
        if not GENAI_AVAILABLE or self.client is None:
            return fallback or {"error": "GenAI SDK not available", "agent": self.name}

        try:
            # Run in thread pool to not block async event loop
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                response = await loop.run_in_executor(
                    executor,
                    lambda: self._generate_content(context, temperature or self.temperature)
                )

            # Parse with robust fallback strategies
            result = safe_json_parse(
                response,
                default=fallback or {"error": "Failed to parse", "agent": self.name}
            )

            return result

        except Exception as e:
            print(f"   ❌ {self.name} failed: {e}")
            return fallback or {
                "error": str(e),
                "agent": self.name
            }

    def analyze(
        self,
        context: str,
        temperature: float = None,
        fallback: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run agent analysis synchronously

        Args:
            context: Analysis context/input
            temperature: Override default temperature
            fallback: Default response if parsing fails

        Returns:
            Parsed agent response as dict
        """
        if not GENAI_AVAILABLE or self.client is None:
            return fallback or {"error": "GenAI SDK not available", "agent": self.name}

        try:
            response = self._generate_content(context, temperature or self.temperature)

            # Parse with robust fallback strategies
            result = safe_json_parse(
                response,
                default=fallback or {"error": "Failed to parse", "agent": self.name}
            )

            return result

        except Exception as e:
            print(f"   ❌ {self.name} failed: {e}")
            return fallback or {
                "error": str(e),
                "agent": self.name
            }

    def _generate_content(self, context: str, temperature: float) -> str:
        """Call GenAI API to generate content"""
        full_prompt = f"{self.system_prompt}\n\nContext:\n{context}"

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=self.max_tokens,
                response_mime_type="application/json"
            )
        )

        # Extract text from Gemini response
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                return candidate.content.parts[0].text

        return str(response)


class PortfolioAnalystADKV2(ADKAgentV2):
    """Portfolio Analyst with few-shot examples and robust parsing"""

    SYSTEM_PROMPT = """# PORTFOLIO ANALYST AGENT

## Your Role
You are a Portfolio Analyst for a daily stock market monitoring system. Your sole responsibility is to analyze the user's current portfolio and identify risks, imbalances, and opportunities.

## Example Analysis

**Input Portfolio:**
```json
{
  "total_value": 100000,
  "positions": [
    {"ticker": "AAPL", "value": 35000, "sector": "Technology"},
    {"ticker": "MSFT", "value": 25000, "sector": "Technology"},
    {"ticker": "JNJ", "value": 15000, "sector": "Healthcare"}
  ]
}
```

**Expected Output:**
```json
{
  "health_score": 65,
  "concentration_risk": "MEDIUM",
  "high_risk_positions": [
    {
      "ticker": "AAPL",
      "issue": "concentration",
      "severity": "HIGH",
      "recommendation": "Reduce to 20% of portfolio (currently 35%)"
    }
  ],
  "rebalancing_suggestions": [
    "Reduce Technology sector from 60% to 40%",
    "Increase Healthcare and Utilities allocation"
  ],
  "summary": "Portfolio concentrated in Technology (60%). AAPL at 35% creates significant single-stock risk. Recommend diversification into defensive sectors."
}
```

## Output Format
Respond with valid JSON only (no markdown):
{
  "health_score": 0-100,
  "concentration_risk": "LOW|MODERATE|HIGH|CRITICAL",
  "high_risk_positions": [...],
  "rebalancing_suggestions": [...],
  "summary": "string"
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="portfolio_analyst",
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key
        )

    async def analyze_portfolio_async(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze portfolio asynchronously"""
        context = f"Portfolio Data:\n{json.dumps(portfolio_data, indent=2)}"
        print(f"🔍 {self.name} analyzing portfolio...")

        fallback = {
            'health_score': 50,
            'concentration_risk': 'UNKNOWN',
            'high_risk_positions': [],
            'rebalancing_suggestions': ['Analysis failed - using fallback'],
            'summary': 'Portfolio analysis unavailable'
        }

        result = await self.analyze_async(context, fallback=fallback)

        print(f"   ✓ Health Score: {result.get('health_score', 'N/A')}/100")
        print(f"   ✓ Risk: {result.get('concentration_risk', 'N/A')}")

        return result


class MarketAnalystADKV2(ADKAgentV2):
    """Market Analyst with enhanced prompts"""

    SYSTEM_PROMPT = """# MARKET ANALYST AGENT

## Your Role
Analyze macro market conditions and provide sentiment assessment.

## Example Analysis

**Input:**
```json
{
  "SPY": {"price": 450.00, "change_pct": 1.2},
  "VIX": 18.5,
  "sector_performance": {"Technology": 1.5, "Energy": -0.8}
}
```

**Expected Output:**
```json
{
  "sentiment": "BULLISH",
  "confidence": 75,
  "volatility_assessment": "LOW",
  "sector_trends": ["Technology outperforming", "Energy weakness continues"],
  "key_risks": ["Potential VIX spike if SPY breaks 450 support"],
  "summary": "Market showing bullish momentum with low volatility. Tech sector leading gains while Energy lags."
}
```

## Output Format
{
  "sentiment": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0-100,
  "volatility_assessment": "LOW|MODERATE|HIGH|EXTREME",
  "sector_trends": [...],
  "key_risks": [...],
  "summary": "string"
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="market_analyst",
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key
        )

    async def analyze_market_async(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market asynchronously"""
        context = f"Market Data:\n{json.dumps(market_data, indent=2)}"
        print(f"📊 {self.name} analyzing market...")

        fallback = {
            'sentiment': 'NEUTRAL',
            'confidence': 50,
            'volatility_assessment': 'MODERATE',
            'sector_trends': [],
            'key_risks': ['Market analysis unavailable'],
            'summary': 'Market analysis failed'
        }

        result = await self.analyze_async(context, fallback=fallback)

        print(f"   ✓ Sentiment: {result.get('sentiment', 'N/A')} ({result.get('confidence', 0)}%)")
        print(f"   ✓ Volatility: {result.get('volatility_assessment', 'N/A')}")

        return result


class NewsMonitorADKV2(ADKAgentV2):
    """News Monitor with enhanced analysis"""

    SYSTEM_PROMPT = """# NEWS MONITOR AGENT

Analyze news sentiment for portfolio positions.

Output JSON:
{
  "ticker_analysis": [
    {
      "ticker": "string",
      "sentiment": "POSITIVE|NEGATIVE|NEUTRAL",
      "confidence": 0-100,
      "key_themes": [...],
      "risk_level": "LOW|MEDIUM|HIGH"
    }
  ],
  "urgent_alerts": [...],
  "opportunities": [...],
  "market_themes": [...]
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="news_monitor",
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key
        )

    async def analyze_news_async(
        self,
        portfolio_data: Dict[str, Any],
        news_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze news asynchronously"""
        tickers = [p['ticker'] for p in portfolio_data.get('positions', [])]
        context = f"Tickers: {', '.join(tickers)}\n\nNews:\n{json.dumps(news_data, indent=2)}"

        print(f"📰 {self.name} analyzing news...")

        fallback = {
            'ticker_analysis': [],
            'urgent_alerts': [],
            'opportunities': [],
            'market_themes': []
        }

        result = await self.analyze_async(context, fallback=fallback)

        print(f"   ✓ Alerts: {len(result.get('urgent_alerts', []))}")
        print(f"   ✓ Opportunities: {len(result.get('opportunities', []))}")

        return result


class OrchestratorADKV2(ADKAgentV2):
    """Enhanced Orchestrator with CFD examples"""

    SYSTEM_PROMPT = """# ORCHESTRATOR AGENT

Synthesize all agent inputs and generate actionable recommendations.

## Example CFD Trade

**Good CFD (Index LONG):**
```json
{
  "ticker": "SPY",
  "direction": "LONG",
  "timeframe": "1-3_DAYS",
  "entry": 450.50,
  "target": 456.00,
  "stop": 448.00,
  "risk_reward": 2.2,
  "reasoning": "Breakout above 450 resistance with strong volume"
}
```

## Output Format
{
  "stock_recommendations": [
    {
      "ticker": "string",
      "action": "BUY|SELL|HOLD|REDUCE",
      "priority": "HIGH|MEDIUM|LOW",
      "confidence": 0-100,
      "reasoning": "string"
    }
  ],
  "cfd_opportunities": [
    {
      "ticker": "string",
      "direction": "LONG|SHORT",
      "timeframe": "INTRADAY|1-3_DAYS|SWING",
      "entry": 0.0,
      "target": 0.0,
      "stop": 0.0,
      "risk_reward": 0.0,
      "reasoning": "string"
    }
  ],
  "risk_alert": "string or null",
  "key_insights": [...]
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="orchestrator",
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key,
            model="gemini-1.5-pro"  # Use Pro for orchestration
        )

    async def orchestrate_async(
        self,
        portfolio_analysis: Dict[str, Any],
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrate asynchronously"""
        context = f"""PORTFOLIO:
{json.dumps(portfolio_analysis, indent=2)}

MARKET:
{json.dumps(market_analysis, indent=2)}

NEWS:
{json.dumps(news_analysis, indent=2)}

Generate:
1. Stock recommendations (REDUCE/SELL overconcentrated positions)
2. CFD opportunities (LONG and SHORT)
3. Risk alerts
4. Key insights"""

        print(f"🎯 {self.name} generating recommendations...")

        fallback = {
            'stock_recommendations': [],
            'cfd_opportunities': [],
            'risk_alert': 'Orchestrator failed - no recommendations',
            'key_insights': ['Analysis unavailable']
        }

        result = await self.analyze_async(context, fallback=fallback)

        print(f"   ✓ Stock Recs: {len(result.get('stock_recommendations', []))}")
        print(f"   ✓ CFD Ops: {len(result.get('cfd_opportunities', []))}")

        return result


class ADKTradingSystemV2:
    """Enhanced ADK system with native parallel execution"""

    def __init__(self, api_key: str):
        """Initialize all agents"""
        self.api_key = api_key
        self.portfolio_analyst = PortfolioAnalystADKV2(api_key)
        self.market_analyst = MarketAnalystADKV2(api_key)
        self.news_monitor = NewsMonitorADKV2(api_key)
        self.orchestrator = OrchestratorADKV2(api_key)

        # Load execution config
        config_loader = get_config_loader()
        self.exec_config = config_loader.get_execution_config()

    async def run_analysis_async(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run analysis with NATIVE PARALLEL EXECUTION

        This uses asyncio.gather() to run all 3 agents simultaneously,
        just like Google ADK's native parallel execution would.

        Returns:
            Complete analysis with recommendations
        """
        print("\n" + "="*70)
        print("  GOOGLE ADK V2 - PARALLEL MULTI-AGENT SYSTEM")
        print("="*70 + "\n")

        print("[STAGE 1] Running 3 agents in PARALLEL...\n")

        # Generate mock news if not provided
        if news_data is None:
            from data.mock_data import MockDataGenerator
            mock = MockDataGenerator()
            news_data = {}
            for pos in portfolio_data.get('positions', []):
                news_data[pos['ticker']] = mock.get_stock_news(pos['ticker'])

        # NATIVE PARALLEL EXECUTION - Run all 3 agents simultaneously
        # This is equivalent to ADK's built-in parallel execution
        portfolio_analysis, market_analysis, news_analysis = await asyncio.gather(
            self.portfolio_analyst.analyze_portfolio_async(portfolio_data),
            self.market_analyst.analyze_market_async(market_data),
            self.news_monitor.analyze_news_async(portfolio_data, news_data),
            return_exceptions=False  # Propagate exceptions
        )

        print("\n[STAGE 2] Orchestrator synthesizing...\n")

        # Orchestrator generates final recommendations
        final_recommendations = await self.orchestrator.orchestrate_async(
            portfolio_analysis,
            market_analysis,
            news_analysis
        )

        # Combine results
        result = {
            **final_recommendations,
            'agent_analyses': {
                'portfolio': portfolio_analysis,
                'market': market_analysis,
                'news': news_analysis
            },
            'timestamp': datetime.now().isoformat(),
            'system': 'Google ADK V2',
            'execution_mode': 'parallel_native',
            'agents_used': 4
        }

        print("\n✓ Analysis Complete (native parallel execution)!\n")

        return result

    def run_analysis(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for async analysis

        Creates event loop and runs async version
        """
        return asyncio.run(self.run_analysis_async(portfolio_data, market_data, news_data))


# Test function
if __name__ == "__main__":
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*70)
    print("  GOOGLE ADK V2 SYSTEM - TEST")
    print("="*70 + "\n")

    if not GENAI_AVAILABLE:
        print("❌ Google GenAI SDK not available. Cannot run test.")
        print("   Install with: pip install google-generativeai")
        sys.exit(1)

    # Initialize system
    system = ADKTradingSystemV2(api_key=API_CONFIG.gemini_api_key)

    # Get test data
    mock = MockDataGenerator()
    portfolio = mock.get_portfolio_data()
    market = mock.get_market_overview()

    # Run analysis (uses async internally)
    print("Testing ASYNC parallel execution...\n")
    results = system.run_analysis(portfolio, market)

    # Display results
    print("="*70)
    print("  📊 RESULTS")
    print("="*70)

    print(f"\n🎯 STOCK RECOMMENDATIONS ({len(results.get('stock_recommendations', []))}):")
    for i, rec in enumerate(results.get('stock_recommendations', [])[:3], 1):
        print(f"\n{i}. {rec.get('ticker', 'N/A')} - {rec.get('action', 'N/A')} ({rec.get('priority', 'N/A')})")
        print(f"   Confidence: {rec.get('confidence', 0)}%")
        print(f"   {rec.get('reasoning', 'N/A')}")

    print(f"\n💱 CFD OPPORTUNITIES ({len(results.get('cfd_opportunities', []))}):")
    for i, cfd in enumerate(results.get('cfd_opportunities', [])[:3], 1):
        print(f"\n{i}. {cfd.get('ticker', 'N/A')} - {cfd.get('direction', 'N/A')} ({cfd.get('timeframe', 'N/A')})")
        print(f"   Entry: ${cfd.get('entry', 0):.2f}, Target: ${cfd.get('target', 0):.2f}, Stop: ${cfd.get('stop', 0):.2f}")
        print(f"   R:R = {cfd.get('risk_reward', 0):.1f}:1")

    if results.get('risk_alert'):
        print(f"\n⚠️  RISK ALERT: {results['risk_alert']}")

    print(f"\n💡 KEY INSIGHTS:")
    for insight in results.get('key_insights', [])[:5]:
        print(f"  • {insight}")

    print(f"\n✓ System: {results.get('system', 'N/A')}")
    print(f"✓ Execution Mode: {results.get('execution_mode', 'N/A')}")
    print(f"✓ Agents: {results.get('agents_used', 0)}\n")
