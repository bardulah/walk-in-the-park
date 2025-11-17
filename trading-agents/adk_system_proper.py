"""
Google ADK Proper Implementation
Uses ADK's native sub_agents pattern for automatic orchestration

Based on Google ADK documentation:
- Create specialized LlmAgent instances
- Compose them using sub_agents parameter
- ADK engine orchestrates execution automatically
"""
import os
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from utils.json_parser import safe_json_parse
from config.agent_config import get_config_loader

# Try to import Google ADK
try:
    from google.adk.agents import LlmAgent, BaseAgent
    from google import genai
    ADK_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Google ADK not available: {e}")
    print("   Install with: pip install google-adk")
    ADK_AVAILABLE = False


class ADKTradingSystemProper:
    """
    Proper Google ADK implementation using sub_agents pattern

    Architecture:
    - Coordinator (parent LlmAgent)
      ├── Portfolio Analyst (sub-agent)
      ├── Market Analyst (sub-agent)
      ├── News Monitor (sub-agent)
      └── Risk Manager (sub-agent)

    ADK engine automatically orchestrates parallel execution
    """

    def __init__(self, api_key: str):
        """
        Initialize ADK trading system

        Args:
            api_key: Google API key for Gemini models
        """
        if not ADK_AVAILABLE:
            raise ImportError("Google ADK not available. Install with: pip install google-adk")

        self.api_key = api_key

        # Load configuration
        config_loader = get_config_loader()

        # Create specialized sub-agents
        self.portfolio_analyst = self._create_portfolio_analyst()
        self.market_analyst = self._create_market_analyst()
        self.news_monitor = self._create_news_monitor()
        self.risk_manager = self._create_risk_manager()

        # Create coordinator with sub-agents
        # ADK will automatically orchestrate them in parallel
        self.coordinator = LlmAgent(
            name="TradingCoordinator",
            model="gemini-2.0-flash-exp",
            description="""I am the Trading System Coordinator. I manage a team of specialized
analysts to generate comprehensive trading recommendations.

My team includes:
- Portfolio Analyst: Analyzes portfolio health and concentration risks
- Market Analyst: Assesses market sentiment and volatility
- News Monitor: Tracks news sentiment for positions
- Risk Manager: Enforces risk limits with override authority

I coordinate their analysis and synthesize final recommendations including:
1. Stock actions (BUY/SELL/HOLD/REDUCE) with reasoning
2. CFD trading opportunities (LONG/SHORT with entry/exit/stop levels)
3. Risk alerts if portfolio is in danger
4. Key actionable insights

I ensure all recommendations are:
- Backed by multi-agent consensus
- Risk-adjusted and position-sized appropriately
- Actionable with specific entry/exit levels
- Prioritized by urgency and confidence
""",
            sub_agents=[
                self.portfolio_analyst,
                self.market_analyst,
                self.news_monitor,
                self.risk_manager
            ],
            api_key=api_key
        )

    def _create_portfolio_analyst(self) -> LlmAgent:
        """Create Portfolio Analyst sub-agent"""
        config = get_config_loader().get_agent_config('portfolio_analyst')

        return LlmAgent(
            name="PortfolioAnalyst",
            model="gemini-1.5-flash",
            description="""I analyze portfolio health and identify concentration risks.

I assess:
- Portfolio health score (0-100)
- Concentration risk levels (positions > 20% are risky)
- Sector distribution and imbalances
- Specific positions requiring rebalancing

Example Analysis:
Input: Portfolio with AAPL at 35%, MSFT at 25% (Total Tech: 60%)
Output:
{
  "health_score": 65,
  "concentration_risk": "HIGH",
  "findings": ["Tech sector 60% - too concentrated", "AAPL 35% - single-stock risk"],
  "recommendations": ["Reduce AAPL to 20%", "Diversify into Healthcare/Utilities"]
}

I provide factual, objective portfolio construction analysis.""",
            api_key=self.api_key
        )

    def _create_market_analyst(self) -> LlmAgent:
        """Create Market Analyst sub-agent"""
        return LlmAgent(
            name="MarketAnalyst",
            model="gemini-1.5-flash",
            description="""I analyze macro market conditions and sentiment.

I assess:
- Market sentiment (BULLISH/BEARISH/NEUTRAL)
- Volatility levels (VIX analysis)
- Sector rotation trends
- Key macro risks

Example Analysis:
Input: SPY +1.2%, VIX 18.5, Tech sector +1.5%
Output:
{
  "sentiment": "BULLISH",
  "confidence": 75,
  "volatility": "LOW",
  "trends": ["Tech sector outperforming", "Low vol environment"],
  "risks": ["VIX could spike if SPY breaks 450 support"]
}

I provide macro market context for stock decisions.""",
            api_key=self.api_key
        )

    def _create_news_monitor(self) -> LlmAgent:
        """Create News Monitor sub-agent"""
        return LlmAgent(
            name="NewsMonitor",
            model="gemini-1.5-flash",
            description="""I monitor news sentiment for portfolio positions.

I identify:
- Positive catalysts and opportunities
- Negative news requiring urgent action
- Sentiment per ticker (POSITIVE/NEGATIVE/NEUTRAL)
- Risk levels from news events

Example Analysis:
Input: AAPL - New product launch, TSLA - Recall news
Output:
{
  "AAPL": {"sentiment": "POSITIVE", "catalyst": "Product launch", "risk": "LOW"},
  "TSLA": {"sentiment": "NEGATIVE", "alert": "Safety recall", "risk": "HIGH"},
  "urgent_alerts": ["TSLA recall - consider reducing position"],
  "opportunities": ["AAPL product cycle - potential strength"]
}

I provide news-driven trading signals.""",
            api_key=self.api_key
        )

    def _create_risk_manager(self) -> LlmAgent:
        """Create Risk Manager sub-agent"""
        return LlmAgent(
            name="RiskManager",
            model="gemini-1.5-flash",
            description="""I enforce portfolio risk limits with override authority.

Risk Rules:
- Max single position: 15%
- Max sector concentration: 40%
- Max portfolio risk per day: 2%
- Max CFD position: 5%
- Min risk/reward ratio: 1.5:1

I have FINAL AUTHORITY to:
- REJECT recommendations violating risk limits
- FORCE immediate reduction of overconcentrated positions
- BLOCK CFD trades with poor risk/reward

Example:
Input: Recommendation to buy NVDA (would make Tech 65% of portfolio)
Output:
{
  "decision": "REJECT",
  "reason": "Would push Tech sector to 65% (limit: 40%)",
  "forced_action": "Must reduce AAPL or MSFT first"
}

I prioritize capital preservation over returns.""",
            api_key=self.api_key
        )

    def run_analysis(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run trading analysis using ADK's automatic orchestration

        Args:
            portfolio_data: Current portfolio positions
            market_data: Market indices and conditions
            news_data: News per ticker (optional)

        Returns:
            Comprehensive trading recommendations
        """
        print("\n" + "="*70)
        print("  GOOGLE ADK PROPER - AUTOMATIC ORCHESTRATION")
        print("="*70 + "\n")

        # Prepare context for all agents
        if news_data is None:
            from data.mock_data import MockDataGenerator
            mock = MockDataGenerator()
            news_data = {}
            for pos in portfolio_data.get('positions', []):
                news_data[pos['ticker']] = mock.get_stock_news(pos['ticker'])

        # Create unified context
        context = f"""Today's Date: {datetime.now().strftime('%Y-%m-%d')}

PORTFOLIO DATA:
{json.dumps(portfolio_data, indent=2)}

MARKET DATA:
{json.dumps(market_data, indent=2)}

NEWS DATA:
{json.dumps(news_data, indent=2)}

TASK:
Analyze this trading scenario and generate comprehensive recommendations.

The Portfolio Analyst, Market Analyst, News Monitor, and Risk Manager will each
contribute their specialized analysis. You must synthesize their inputs and provide:

1. STOCK RECOMMENDATIONS: List of stocks to BUY/SELL/HOLD/REDUCE with:
   - Ticker symbol
   - Action (BUY/SELL/HOLD/REDUCE)
   - Priority (HIGH/MEDIUM/LOW)
   - Confidence (0-100)
   - Reasoning (2-3 sentences combining all agent insights)
   - Target price and stop loss if applicable

2. CFD TRADING OPPORTUNITIES: Short-term trades (intraday to 3 days) with:
   - Ticker (SPY, QQQ, or high-volume stocks)
   - Direction (LONG/SHORT)
   - Entry level
   - Target level
   - Stop loss
   - Risk/reward ratio
   - Position size (2-5% of capital)
   - Reasoning (technical + catalyst)

3. RISK ALERTS: Any portfolio violations or urgent actions required

4. KEY INSIGHTS: Top 5 actionable insights from all analysts

Output strict JSON format:
{{
  "stock_recommendations": [
    {{
      "ticker": "string",
      "action": "BUY|SELL|HOLD|REDUCE",
      "priority": "HIGH|MEDIUM|LOW",
      "confidence": 0-100,
      "reasoning": "string",
      "target_price": 0.0,
      "stop_loss": 0.0
    }}
  ],
  "cfd_opportunities": [
    {{
      "ticker": "string",
      "direction": "LONG|SHORT",
      "timeframe": "INTRADAY|1-3_DAYS",
      "entry": 0.0,
      "target": 0.0,
      "stop": 0.0,
      "risk_reward": 0.0,
      "position_size_pct": 2-5,
      "reasoning": "string"
    }}
  ],
  "risk_alert": "string or null",
  "key_insights": ["insight1", "insight2", "insight3", "insight4", "insight5"]
}}"""

        print("Running ADK analysis with automatic sub-agent orchestration...\n")

        # ADK automatically orchestrates sub-agents in parallel!
        # The coordinator will invoke sub-agents as needed
        response = self.coordinator.run(context)

        print("\n✓ ADK orchestration complete!\n")

        # Parse response with robust fallback
        result = safe_json_parse(
            str(response),
            default={
                'stock_recommendations': [],
                'cfd_opportunities': [],
                'risk_alert': 'Analysis parsing failed',
                'key_insights': ['ADK orchestration completed but parsing failed']
            }
        )

        # Add metadata
        result['timestamp'] = datetime.now().isoformat()
        result['system'] = 'Google ADK Proper'
        result['execution_mode'] = 'automatic_orchestration'
        result['coordinator'] = 'TradingCoordinator'
        result['sub_agents'] = 4

        return result


# Test function
if __name__ == "__main__":
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*70)
    print("  GOOGLE ADK PROPER IMPLEMENTATION - TEST")
    print("="*70 + "\n")

    if not ADK_AVAILABLE:
        print("❌ Google ADK not available. Cannot run test.")
        print("   Install with: pip install google-adk")
        sys.exit(1)

    try:
        # Initialize system
        print("Initializing ADK trading system...")
        system = ADKTradingSystemProper(api_key=API_CONFIG.gemini_api_key)

        # Get test data
        mock = MockDataGenerator()
        portfolio = mock.get_portfolio_data()
        market = mock.get_market_overview()

        print("Portfolio value: $" + f"{portfolio['total_value']:,.2f}")
        print(f"Positions: {len(portfolio['positions'])}")
        print(f"Market: SPY ${market.get('indices', {}).get('SPY', {}).get('price', 'N/A')}\n")

        # Run analysis
        results = system.run_analysis(portfolio, market)

        # Display results
        print("="*70)
        print("  📊 RESULTS")
        print("="*70)

        print(f"\n🎯 STOCK RECOMMENDATIONS ({len(results.get('stock_recommendations', []))}):")
        for i, rec in enumerate(results.get('stock_recommendations', [])[:5], 1):
            print(f"\n{i}. {rec.get('ticker', 'N/A')} - {rec.get('action', 'N/A')} ({rec.get('priority', 'N/A')} priority)")
            print(f"   Confidence: {rec.get('confidence', 0)}%")
            print(f"   {rec.get('reasoning', 'N/A')}")

        print(f"\n💱 CFD OPPORTUNITIES ({len(results.get('cfd_opportunities', []))}):")
        for i, cfd in enumerate(results.get('cfd_opportunities', [])[:5], 1):
            print(f"\n{i}. {cfd.get('ticker', 'N/A')} - {cfd.get('direction', 'N/A')} ({cfd.get('timeframe', 'N/A')})")
            print(f"   Entry: ${cfd.get('entry', 0):.2f}, Target: ${cfd.get('target', 0):.2f}, Stop: ${cfd.get('stop', 0):.2f}")
            print(f"   R:R = {cfd.get('risk_reward', 0):.1f}:1, Size: {cfd.get('position_size_pct', 0)}%")

        if results.get('risk_alert'):
            print(f"\n⚠️  RISK ALERT: {results['risk_alert']}")

        print(f"\n💡 KEY INSIGHTS:")
        for insight in results.get('key_insights', [])[:5]:
            print(f"  • {insight}")

        print(f"\n✓ System: {results.get('system', 'N/A')}")
        print(f"✓ Execution: {results.get('execution_mode', 'N/A')}")
        print(f"✓ Sub-Agents: {results.get('sub_agents', 0)}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
