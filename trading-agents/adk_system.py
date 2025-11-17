"""
Google ADK-based Multi-Agent Trading System
Uses Google's GenAI SDK for agent-to-agent communication
"""
import os
import json
from typing import Dict, Any, List
from datetime import datetime
from google import genai
from google.genai import types


class ADKAgent:
    """Base class for ADK-based agents"""

    def __init__(self, name: str, model: str, system_prompt: str, api_key: str):
        """
        Initialize ADK agent

        Args:
            name: Agent name
            model: Model to use (e.g., 'gemini-1.5-flash')
            system_prompt: Agent's system instructions
            api_key: Google API key
        """
        self.name = name
        self.model_name = model
        self.system_prompt = system_prompt

        # Initialize Google GenAI client
        self.client = genai.Client(api_key=api_key)

    def analyze(self, context: str, temperature: float = 0.7) -> str:
        """
        Run agent analysis

        Args:
            context: Analysis context/input
            temperature: Sampling temperature

        Returns:
            Agent response as JSON string
        """
        try:
            # Create prompt with system instructions + context
            full_prompt = f"{self.system_prompt}\n\nContext:\n{context}"

            # Generate response using Google GenAI
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json"
                )
            )

            # Extract text from Gemini response structure:
            # response format: {candidates: [{content: {parts: [{text: "..."}]}}]}
            if hasattr(response, 'text'):
                # Direct access if available
                return response.text
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                # Parse response structure
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    return candidate.content.parts[0].text

            # Fallback
            return str(response)

        except Exception as e:
            print(f"   ❌ {self.name} failed: {e}")
            return json.dumps({
                "error": str(e),
                "agent": self.name
            })


class PortfolioAnalystADK(ADKAgent):
    """Portfolio Analysis Agent using ADK"""

    SYSTEM_PROMPT = """You are a Portfolio Analyst specializing in portfolio health and risk assessment.

Your role:
1. Analyze portfolio composition and concentration risks
2. Identify positions that violate diversification best practices
3. Calculate portfolio health score (0-100)
4. Flag high-risk positions requiring attention

Output strict JSON:
{
  "health_score": 0-100,
  "concentration_risk": "LOW|MODERATE|HIGH|CRITICAL",
  "high_risk_positions": [
    {
      "ticker": "string",
      "issue": "concentration|loss|volatility",
      "severity": "LOW|MEDIUM|HIGH",
      "recommendation": "string"
    }
  ],
  "rebalancing_suggestions": ["list of suggestions"],
  "summary": "2-3 sentence summary"
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="PortfolioAnalyst",
            model="gemini-1.5-flash",
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key
        )

    def analyze_portfolio(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze portfolio and return structured assessment"""
        context = f"Portfolio Data:\n{json.dumps(portfolio_data, indent=2)}"
        print(f"🔍 {self.name} analyzing portfolio...")
        response = self.analyze(context, temperature=0.3)

        result = json.loads(response)
        print(f"   ✓ Health Score: {result.get('health_score', 'N/A')}/100")
        print(f"   ✓ Risk: {result.get('concentration_risk', 'N/A')}")

        return result


class MarketAnalystADK(ADKAgent):
    """Market Analysis Agent using ADK"""

    SYSTEM_PROMPT = """You are a Market Analyst specializing in macro market conditions.

Your role:
1. Assess overall market sentiment (BULLISH, BEARISH, NEUTRAL)
2. Analyze volatility and risk conditions
3. Identify sector rotation trends
4. Provide market outlook

Output strict JSON:
{
  "sentiment": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0-100,
  "volatility_assessment": "LOW|MODERATE|HIGH|EXTREME",
  "sector_trends": ["trend descriptions"],
  "key_risks": ["risk factors"],
  "summary": "2-3 sentence market summary"
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="MarketAnalyst",
            model="gemini-1.5-flash",
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key
        )

    def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market conditions"""
        context = f"Market Data:\n{json.dumps(market_data, indent=2)}"
        print(f"📊 {self.name} analyzing market...")
        response = self.analyze(context, temperature=0.4)

        result = json.loads(response)
        print(f"   ✓ Sentiment: {result.get('sentiment', 'N/A')} ({result.get('confidence', 'N/A')}%)")
        print(f"   ✓ Volatility: {result.get('volatility_assessment', 'N/A')}")

        return result


class NewsMonitorADK(ADKAgent):
    """News Monitoring Agent using ADK"""

    SYSTEM_PROMPT = """You are a News Analyst monitoring market news and sentiment.

Your role:
1. Analyze news sentiment for each position
2. Identify urgent alerts or catalysts
3. Spot opportunities from positive news
4. Assess news-driven risks

Output strict JSON:
{
  "ticker_analysis": [
    {
      "ticker": "string",
      "sentiment": "POSITIVE|NEGATIVE|NEUTRAL",
      "confidence": 0-100,
      "key_themes": ["themes"],
      "risk_level": "LOW|MEDIUM|HIGH"
    }
  ],
  "urgent_alerts": ["urgent negative news"],
  "opportunities": ["positive catalysts"],
  "market_themes": ["overall themes"]
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="NewsMonitor",
            model="gemini-1.5-flash",
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key
        )

    def analyze_news(self, portfolio_data: Dict[str, Any], news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze news for portfolio positions"""
        tickers = [p['ticker'] for p in portfolio_data.get('positions', [])]
        context = f"""Portfolio Tickers: {', '.join(tickers)}

News Data:
{json.dumps(news_data, indent=2)}"""

        print(f"📰 {self.name} analyzing news...")
        response = self.analyze(context, temperature=0.3)

        result = json.loads(response)
        print(f"   ✓ Alerts: {len(result.get('urgent_alerts', []))}")
        print(f"   ✓ Opportunities: {len(result.get('opportunities', []))}")

        return result


class OrchestratorADK(ADKAgent):
    """Orchestrator Agent coordinating all analysis"""

    SYSTEM_PROMPT = """You are the Orchestrator, the final decision-maker synthesizing all agent inputs.

Your role:
1. Combine Portfolio, Market, and News analysis
2. Generate actionable trading recommendations
3. Provide CFD trading opportunities
4. Resolve conflicts between agents

Output strict JSON:
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
  "key_insights": ["insights"]
}"""

    def __init__(self, api_key: str):
        super().__init__(
            name="Orchestrator",
            model="gemini-1.5-pro",  # Use Pro for final decisions
            system_prompt=self.SYSTEM_PROMPT,
            api_key=api_key
        )

    def orchestrate(
        self,
        portfolio_analysis: Dict[str, Any],
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine all analyses and generate recommendations"""

        context = f"""PORTFOLIO ANALYSIS:
{json.dumps(portfolio_analysis, indent=2)}

MARKET ANALYSIS:
{json.dumps(market_analysis, indent=2)}

NEWS ANALYSIS:
{json.dumps(news_analysis, indent=2)}

Synthesize all inputs and generate:
1. Stock recommendations (REDUCE/SELL overconcentrated positions)
2. CFD trading opportunities (both LONG and SHORT)
3. Risk alerts if portfolio is in danger
4. Key insights"""

        print(f"🎯 {self.name} generating final recommendations...")
        response = self.analyze(context, temperature=0.5)

        result = json.loads(response)
        print(f"   ✓ Stock Recommendations: {len(result.get('stock_recommendations', []))}")
        print(f"   ✓ CFD Opportunities: {len(result.get('cfd_opportunities', []))}")

        return result


class ADKTradingSystem:
    """Complete ADK-based multi-agent trading system"""

    def __init__(self, api_key: str):
        """Initialize all ADK agents"""
        self.portfolio_analyst = PortfolioAnalystADK(api_key)
        self.market_analyst = MarketAnalystADK(api_key)
        self.news_monitor = NewsMonitorADK(api_key)
        self.orchestrator = OrchestratorADK(api_key)

    def run_analysis(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run complete multi-agent analysis

        Args:
            portfolio_data: Current portfolio
            market_data: Market indices and conditions
            news_data: News per ticker (optional, will use mock if None)

        Returns:
            Complete analysis with recommendations
        """
        print("\n" + "="*70)
        print("  GOOGLE ADK MULTI-AGENT TRADING SYSTEM")
        print("="*70 + "\n")

        print("[STAGE 1] Running Agent Analysis...\n")

        # Stage 1: Run specialized agents
        portfolio_analysis = self.portfolio_analyst.analyze_portfolio(portfolio_data)
        market_analysis = self.market_analyst.analyze_market(market_data)

        # Generate mock news if not provided
        if news_data is None:
            from data.mock_data import MockDataGenerator
            mock = MockDataGenerator()
            news_data = {}
            for pos in portfolio_data.get('positions', []):
                news_data[pos['ticker']] = mock.get_stock_news(pos['ticker'])

        news_analysis = self.news_monitor.analyze_news(portfolio_data, news_data)

        print("\n[STAGE 2] Orchestrator synthesizing recommendations...\n")

        # Stage 2: Orchestrator generates final recommendations
        final_recommendations = self.orchestrator.orchestrate(
            portfolio_analysis,
            market_analysis,
            news_analysis
        )

        # Combine all outputs
        result = {
            **final_recommendations,
            'agent_analyses': {
                'portfolio': portfolio_analysis,
                'market': market_analysis,
                'news': news_analysis
            },
            'timestamp': datetime.now().isoformat(),
            'system': 'Google ADK',
            'agents_used': 4
        }

        print("\n✓ Analysis Complete!\n")

        return result


if __name__ == "__main__":
    # Test Google ADK system
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*70)
    print("  GOOGLE ADK TRADING SYSTEM - TEST")
    print("="*70 + "\n")

    # Initialize system
    system = ADKTradingSystem(api_key=API_CONFIG.gemini_api_key)

    # Get test data
    mock = MockDataGenerator()
    portfolio = mock.get_portfolio_data()
    market = mock.get_market_overview()

    # Run analysis
    results = system.run_analysis(portfolio, market)

    # Display results
    print("="*70)
    print("  📊 RESULTS")
    print("="*70)

    print(f"\n🎯 STOCK RECOMMENDATIONS ({len(results.get('stock_recommendations', []))}):")
    for i, rec in enumerate(results.get('stock_recommendations', []), 1):
        print(f"\n{i}. {rec['ticker']} - {rec['action']} ({rec['priority']} priority)")
        print(f"   Confidence: {rec['confidence']}%")
        print(f"   {rec['reasoning']}")

    print(f"\n💱 CFD OPPORTUNITIES ({len(results.get('cfd_opportunities', []))}):")
    for i, cfd in enumerate(results.get('cfd_opportunities', []), 1):
        print(f"\n{i}. {cfd['ticker']} - {cfd['direction']} ({cfd['timeframe']})")
        print(f"   Entry: ${cfd.get('entry', 0):.2f}, Target: ${cfd.get('target', 0):.2f}, Stop: ${cfd.get('stop', 0):.2f}")
        print(f"   R:R = {cfd.get('risk_reward', 0):.1f}:1")
        print(f"   {cfd['reasoning']}")

    if results.get('risk_alert'):
        print(f"\n⚠️  RISK ALERT: {results['risk_alert']}")

    print(f"\n💡 KEY INSIGHTS:")
    for insight in results.get('key_insights', []):
        print(f"  • {insight}")

    print("\n")
