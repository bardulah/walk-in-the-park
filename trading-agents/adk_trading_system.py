"""
Google ADK Trading System - Proper Implementation with Async Support
Based on official ADK documentation and patterns

Installation:
    pip install google-adk

Architecture:
- Uses ParallelAgent for concurrent sub-agent execution
- Agents communicate via session state and output_key
- Coordinator LlmAgent synthesizes final recommendations
- InMemorySessionService for session management
- Runner for execution
- Full async/await support

References:
- https://google.github.io/adk-docs/
- https://github.com/google/adk-python
- https://github.com/google/adk-samples
"""
import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from utils.json_parser import safe_json_parse
from config.agent_config import get_config_loader

# Try to import Google ADK
try:
    from google.adk import Runner
    from google.adk.agents import LlmAgent, ParallelAgent
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    ADK_AVAILABLE = True
    print("✓ Google ADK imported successfully")
except ImportError as e:
    print(f"⚠️  Google ADK not available: {e}")
    print("   Install with: pip install google-adk")
    ADK_AVAILABLE = False


class ADKTradingSystem:
    """
    Proper Google ADK Trading System with async support

    Uses ADK's official patterns:
    - ParallelAgent for concurrent execution
    - LlmAgent with output_key for state management
    - Runner with InMemorySessionService
    - Proper agent hierarchy
    - Full async/await handling
    """

    def __init__(self, api_key: str, app_name: str = "trading_system"):
        """
        Initialize ADK trading system

        Args:
            api_key: Google API key for Gemini models
            app_name: Application name for session management
        """
        if not ADK_AVAILABLE:
            raise ImportError(
                "Google ADK not available. Install with: pip install google-adk"
            )

        self.api_key = api_key
        self.app_name = app_name

        # Load configuration
        self.config_loader = get_config_loader()

        # Initialize session service
        self.session_service = InMemorySessionService()

        # Create specialized agents
        self.portfolio_analyst = self._create_portfolio_analyst()
        self.market_analyst = self._create_market_analyst()
        self.news_monitor = self._create_news_monitor()

        # Create parallel agent to run analysts concurrently
        self.parallel_analysts = ParallelAgent(
            name="ParallelAnalysts",
            sub_agents=[
                self.portfolio_analyst,
                self.market_analyst,
                self.news_monitor
            ],
            description="Runs portfolio, market, and news analysts in parallel"
        )

        # Create coordinator that uses parallel agent
        self.coordinator = self._create_coordinator()

        # Create runner
        self.runner = Runner(
            agent=self.coordinator,
            app_name=self.app_name,
            session_service=self.session_service
        )

    def _create_portfolio_analyst(self) -> LlmAgent:
        """Create Portfolio Analyst agent with proper ADK patterns"""

        instruction = """# PORTFOLIO ANALYST AGENT

## Your Role
You are a Portfolio Analyst for a daily stock market monitoring system.

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
  "concentration_risk": "HIGH",
  "high_risk_positions": [
    {
      "ticker": "AAPL",
      "issue": "concentration",
      "severity": "HIGH",
      "recommendation": "Reduce to 20% of portfolio"
    }
  ],
  "rebalancing_suggestions": [
    "Reduce Technology sector from 60% to 40%",
    "Increase Healthcare allocation"
  ],
  "summary": "Portfolio concentrated in Technology (60%). AAPL at 35% creates significant single-stock risk."
}
```

## Your Task
Analyze the portfolio data from session state (key: portfolio_data) and provide:
1. Portfolio health score (0-100)
2. Concentration risk assessment
3. High-risk positions requiring attention
4. Rebalancing suggestions
5. Summary of findings

Output strict JSON format.
"""

        return LlmAgent(
            name="PortfolioAnalyst",
            model="gemini-1.5-flash",
            description="Analyzes portfolio health and concentration risks",
            instruction=instruction,
            output_key="portfolio_analysis"  # Store result in session state
        )

    def _create_market_analyst(self) -> LlmAgent:
        """Create Market Analyst agent"""

        instruction = """# MARKET ANALYST AGENT

## Your Role
You are a Market Analyst specializing in macro market conditions.

## Example Analysis

**Input Market Data:**
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
  "summary": "Market showing bullish momentum with low volatility."
}
```

## Your Task
Analyze market data from session state (key: market_data) and provide:
1. Market sentiment (BULLISH/BEARISH/NEUTRAL)
2. Confidence level (0-100)
3. Volatility assessment
4. Sector trends
5. Key risks

Output strict JSON format.
"""

        return LlmAgent(
            name="MarketAnalyst",
            model="gemini-1.5-flash",
            description="Analyzes macro market sentiment and volatility",
            instruction=instruction,
            output_key="market_analysis"
        )

    def _create_news_monitor(self) -> LlmAgent:
        """Create News Monitor agent"""

        instruction = """# NEWS MONITOR AGENT

## Your Role
You monitor news sentiment for portfolio positions.

## Your Task
Analyze news data from session state (key: news_data) and provide:
1. Per-ticker sentiment analysis (POSITIVE/NEGATIVE/NEUTRAL)
2. Urgent alerts requiring immediate action
3. Positive opportunities to watch
4. Overall market themes from news

Output strict JSON:
```json
{
  "ticker_analysis": [
    {
      "ticker": "AAPL",
      "sentiment": "POSITIVE",
      "confidence": 85,
      "key_themes": ["Product launch"],
      "risk_level": "LOW"
    }
  ],
  "urgent_alerts": ["TSLA recall - consider reducing position"],
  "opportunities": ["AAPL product cycle - potential strength"],
  "market_themes": ["Tech sector momentum"]
}
```
"""

        return LlmAgent(
            name="NewsMonitor",
            model="gemini-1.5-flash",
            description="Monitors news sentiment and identifies catalysts",
            instruction=instruction,
            output_key="news_analysis"
        )

    def _create_coordinator(self) -> LlmAgent:
        """Create coordinator that orchestrates parallel analysis and synthesis"""

        instruction = """# TRADING COORDINATOR

## Your Role
You are the Trading System Coordinator. You orchestrate a team of analysts
running in parallel and synthesize their findings into actionable trading recommendations.

## Your Team (Runs in Parallel)
- Portfolio Analyst: Analyzes portfolio health (output: portfolio_analysis)
- Market Analyst: Assesses market conditions (output: market_analysis)
- News Monitor: Tracks news sentiment (output: news_analysis)

## Your Task
1. First, delegate to the ParallelAnalysts agent to run all three analysts concurrently
2. After the parallel analysis completes, read their results from session state keys:
   - portfolio_analysis (from Portfolio Analyst)
   - market_analysis (from Market Analyst)
   - news_analysis (from News Monitor)
3. Synthesize their findings into comprehensive trading recommendations

## Output Format

Generate comprehensive trading recommendations in strict JSON:

```json
{
  "stock_recommendations": [
    {
      "ticker": "AAPL",
      "action": "BUY|SELL|HOLD|REDUCE",
      "priority": "HIGH|MEDIUM|LOW",
      "confidence": 75,
      "reasoning": "Combined insights from all analysts",
      "target_price": 180.00,
      "stop_loss": 165.00
    }
  ],
  "cfd_opportunities": [
    {
      "ticker": "SPY",
      "direction": "LONG|SHORT",
      "timeframe": "INTRADAY|1-3_DAYS",
      "entry": 450.50,
      "target": 456.00,
      "stop": 448.00,
      "risk_reward": 2.2,
      "position_size_pct": 4,
      "reasoning": "Technical setup + market catalyst"
    }
  ],
  "risk_alert": "Portfolio concentrated in Tech - reduce AAPL",
  "key_insights": [
    "Insight 1 from multi-agent analysis",
    "Insight 2 combining market and news",
    "Insight 3 from portfolio health",
    "Insight 4 about opportunities",
    "Insight 5 about risks"
  ]
}
```

## CFD Trade Guidelines
- Mix of index CFDs (SPY, QQQ) and stock CFDs
- Both LONG (breakouts, momentum) and SHORT (breakdowns)
- Entry/target/stop levels based on technical analysis
- 2-5% position size per trade
- Min 1.5:1 risk/reward ratio
- Clear catalysts from news and market analysis

## Stock Recommendation Guidelines
- REDUCE/SELL for overconcentrated positions (from portfolio analysis)
- BUY for new opportunities (from market + news)
- HOLD for well-positioned holdings
- Specific entry/exit levels
- Risk-adjusted position sizing
"""

        return LlmAgent(
            name="TradingCoordinator",
            model="gemini-2.0-flash-exp",  # Use latest model for coordination
            description="Coordinates parallel analysis and synthesizes trading recommendations",
            instruction=instruction,
            sub_agents=[self.parallel_analysts],  # Include parallel agent as sub-agent
            output_key="final_recommendations"
        )

    async def run_analysis_async(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Run trading analysis using ADK's Runner pattern (async)

        Args:
            portfolio_data: Current portfolio positions
            market_data: Market indices and conditions
            news_data: News per ticker (optional)
            user_id: User identifier for session management

        Returns:
            Trading recommendations
        """
        print("\n" + "="*70)
        print("  GOOGLE ADK TRADING SYSTEM - OFFICIAL IMPLEMENTATION")
        print("="*70 + "\n")

        # Prepare news data if not provided
        if news_data is None:
            from data.mock_data import MockDataGenerator
            mock = MockDataGenerator()
            news_data = {}
            for pos in portfolio_data.get('positions', []):
                news_data[pos['ticker']] = mock.get_stock_news(pos['ticker'])

        # Create initial session state with all input data
        initial_state = {
            "portfolio_data": portfolio_data,
            "market_data": market_data,
            "news_data": news_data,
            "timestamp": datetime.now().isoformat()
        }

        # Create session (ASYNC)
        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            state=initial_state
        )

        print(f"Created session: {session.id}")
        print(f"Portfolio value: ${portfolio_data.get('total_value', 0):,.2f}")
        print(f"Positions: {len(portfolio_data.get('positions', []))}\n")

        # Create user message
        user_message = types.Content(
            role='user',
            parts=[types.Part(text=f"""Analyze this trading scenario and provide recommendations.

Today's Date: {datetime.now().strftime('%Y-%m-%d')}

The portfolio, market, and news data are in the session state.

Please:
1. Run your ParallelAnalysts to analyze portfolio, market, and news simultaneously
2. Synthesize their findings from session state
3. Generate comprehensive trading recommendations (stocks + CFDs)

Provide actionable recommendations with specific entry/exit levels.""")]
        )

        print("[STAGE 1] Running parallel analysis (Portfolio + Market + News)...\n")

        # Run agent via Runner (async)
        events = []
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=user_message
        ):
            events.append(event)
            # Print agent progress
            if hasattr(event, 'message') and event.message:
                parts = event.message.parts if hasattr(event.message, 'parts') else []
                if parts:
                    content = parts[0].text if hasattr(parts[0], 'text') else str(parts[0])
                    if content and len(content) < 200:
                        print(f"  {content}")

        print("\n[STAGE 2] Coordinator synthesizing recommendations...\n")

        # Get final result from session state (ASYNC)
        updated_session = await self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session.id
        )

        # Extract final recommendations from state
        final_recs = updated_session.state.get('final_recommendations', {})

        # Parse with robust fallback
        if isinstance(final_recs, str):
            result = safe_json_parse(
                final_recs,
                default={
                    'stock_recommendations': [],
                    'cfd_opportunities': [],
                    'risk_alert': 'Parsing failed',
                    'key_insights': ['Analysis completed but parsing failed']
                }
            )
        else:
            result = final_recs if isinstance(final_recs, dict) else {}

        # Add metadata
        result['timestamp'] = datetime.now().isoformat()
        result['system'] = 'Google ADK Official'
        result['execution_mode'] = 'parallel_with_adk'
        result['session_id'] = session.id

        # Include individual agent analyses
        result['agent_analyses'] = {
            'portfolio': updated_session.state.get('portfolio_analysis', {}),
            'market': updated_session.state.get('market_analysis', {}),
            'news': updated_session.state.get('news_analysis', {})
        }

        print("✓ Analysis complete!\n")

        return result

    def run_analysis(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for run_analysis_async

        Args:
            portfolio_data: Current portfolio positions
            market_data: Market indices and conditions
            news_data: News per ticker (optional)
            user_id: User identifier for session management

        Returns:
            Trading recommendations
        """
        return asyncio.run(
            self.run_analysis_async(portfolio_data, market_data, news_data, user_id)
        )


# Test function
if __name__ == "__main__":
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*70)
    print("  GOOGLE ADK TRADING SYSTEM - TEST")
    print("="*70 + "\n")

    if not ADK_AVAILABLE:
        print("❌ Google ADK not available.")
        print("   Install with: pip install google-adk")
        sys.exit(1)

    try:
        # Initialize system
        print("Initializing ADK trading system...")
        system = ADKTradingSystem(api_key=API_CONFIG.gemini_api_key)

        # Get test data
        mock = MockDataGenerator()
        portfolio = mock.get_portfolio_data()
        market = mock.get_market_overview()

        print("✓ System initialized\n")

        # Run analysis
        results = system.run_analysis(portfolio, market)

        # Display results
        print("="*70)
        print("  📊 RESULTS")
        print("="*70)

        print(f"\n🎯 STOCK RECOMMENDATIONS ({len(results.get('stock_recommendations', []))}):")
        for i, rec in enumerate(results.get('stock_recommendations', [])[:5], 1):
            print(f"\n{i}. {rec.get('ticker', 'N/A')} - {rec.get('action', 'N/A')} ({rec.get('priority', 'N/A')})")
            print(f"   Confidence: {rec.get('confidence', 0)}%")
            reasoning = rec.get('reasoning', 'N/A')
            print(f"   {reasoning[:100]}{'...' if len(reasoning) > 100 else ''}")

        print(f"\n💱 CFD OPPORTUNITIES ({len(results.get('cfd_opportunities', []))}):")
        for i, cfd in enumerate(results.get('cfd_opportunities', [])[:5], 1):
            print(f"\n{i}. {cfd.get('ticker', 'N/A')} - {cfd.get('direction', 'N/A')}")
            print(f"   Entry: ${cfd.get('entry', 0):.2f} → Target: ${cfd.get('target', 0):.2f}")
            print(f"   R:R = {cfd.get('risk_reward', 0):.1f}:1, Size: {cfd.get('position_size_pct', 0)}%")

        if results.get('risk_alert'):
            print(f"\n⚠️  RISK ALERT: {results['risk_alert']}")

        print(f"\n💡 KEY INSIGHTS:")
        for insight in results.get('key_insights', [])[:5]:
            print(f"  • {insight}")

        print(f"\n✓ System: {results.get('system', 'N/A')}")
        print(f"✓ Execution Mode: {results.get('execution_mode', 'N/A')}")
        print(f"✓ Session ID: {results.get('session_id', 'N/A')}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
