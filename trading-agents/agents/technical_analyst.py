"""
Technical Analyst Agent
Analyzes price action, chart patterns, and technical indicators
"""
import json
from typing import Dict, Any, List
from utils.json_parser import safe_json_parse


class TechnicalAnalyst:
    """Analyzes technical indicators and chart patterns"""

    def __init__(self, llm_router):
        """
        Initialize Technical Analyst

        Args:
            llm_router: LLM router for model calls
        """
        self.llm_router = llm_router
        self.model = "gemini-flash-or"  # Fast for technical analysis

    def analyze(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze technical indicators for portfolio positions

        Args:
            portfolio_data: Current portfolio positions
            market_data: Market indices and volatility data

        Returns:
            Technical analysis with signals and patterns
        """
        system_prompt = """You are a Technical Analyst specializing in chart patterns and technical indicators.

Your role is to:
1. Analyze price action and momentum for each position
2. Identify key support/resistance levels
3. Assess technical strength (overbought/oversold conditions)
4. Identify chart patterns (head and shoulders, double tops, breakouts, etc.)
5. Provide buy/sell/hold signals based on technicals

For each stock, consider:
- Price relative to moving averages (50-day, 200-day)
- RSI (overbought >70, oversold <30)
- MACD signals
- Volume trends
- Support/resistance levels
- Chart patterns

Output strict JSON format:
{
  "ticker_analysis": [
    {
      "ticker": "AAPL",
      "technical_signal": "BUY|SELL|HOLD",
      "confidence": 0-100,
      "strength": "STRONG|MODERATE|WEAK",
      "trend": "BULLISH|BEARISH|SIDEWAYS",
      "rsi_status": "OVERSOLD|NEUTRAL|OVERBOUGHT",
      "key_levels": {"support": 170, "resistance": 185},
      "patterns": ["Pattern names if any"],
      "reasoning": "Brief technical rationale"
    }
  ],
  "market_technical_condition": "Overall market technical health",
  "volatility_assessment": "VIX and volatility analysis",
  "sector_rotation": "Technical signs of sector rotation"
}"""

        # Build context
        tickers = [pos['ticker'] for pos in portfolio_data.get('positions', [])]
        positions_summary = []

        for pos in portfolio_data.get('positions', []):
            positions_summary.append({
                'ticker': pos['ticker'],
                'current_price': pos['current_price'],
                'avg_cost': pos['avg_cost'],
                'unrealized_pnl_pct': pos['unrealized_pnl_pct']
            })

        user_prompt = f"""Perform technical analysis for portfolio positions.

Positions:
{json.dumps(positions_summary, indent=2)}

Market Conditions:
{json.dumps(market_data.get('indices', {}), indent=2)}
VIX: {market_data.get('vix_level', 'N/A')}
Market Sentiment: {market_data.get('sentiment_signal', 'N/A')}

Based on current market conditions and technical indicators, provide:
1. Technical signal for each position
2. Key support/resistance levels
3. Chart patterns or technical setups
4. Overall market technical health
5. Volatility assessment

Note: Use reasonable technical assumptions for moving averages, RSI, MACD based on price action and market conditions."""

        print(f"📈 Technical Analyst analyzing {len(tickers)} positions...")

        try:
            response = self.llm_router.call(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                max_tokens=2500,
                json_mode=True
            )

            # Parse JSON response with robust fallback strategies
            fallback = {
                'ticker_analysis': [],
                'market_technical_condition': 'Analysis parsing failed',
                'volatility_assessment': 'Parsing failed',
                'sector_rotation': '',
                'agent': 'TechnicalAnalyst',
                'fallback': True
            }

            analysis = safe_json_parse(response, default=fallback)

            # Add metadata
            analysis['agent'] = 'TechnicalAnalyst'
            analysis['model_used'] = self.model

            print(f"   ✓ Analysis complete")

            # Count signals
            signals = {}
            for ticker_analysis in analysis.get('ticker_analysis', []):
                signal = ticker_analysis.get('technical_signal', 'HOLD')
                signals[signal] = signals.get(signal, 0) + 1

            print(f"   Signals: {signals}")

            return analysis

        except Exception as e:
            print(f"   ❌ Technical analysis failed: {e}")
            return {
                'ticker_analysis': [],
                'market_technical_condition': 'Analysis failed',
                'volatility_assessment': f'Error: {str(e)}',
                'sector_rotation': '',
                'agent': 'TechnicalAnalyst',
                'error': str(e)
            }


if __name__ == "__main__":
    # Test Technical Analyst
    from config.llm_router_unified import UnifiedLLMRouter
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*60)
    print("  TECHNICAL ANALYST AGENT - TEST")
    print("="*60 + "\n")

    # Initialize
    llm_router = UnifiedLLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )

    technical_analyst = TechnicalAnalyst(llm_router)
    mock_data = MockDataGenerator()

    # Get test data
    portfolio = mock_data.get_portfolio_data()
    market = mock_data.get_market_overview()

    # Run analysis
    result = technical_analyst.analyze(portfolio, market)

    # Display results
    print("\n📈 TECHNICAL ANALYSIS:")
    print(f"\nMarket Technical Condition: {result.get('market_technical_condition', 'N/A')}")
    print(f"Volatility Assessment: {result.get('volatility_assessment', 'N/A')}")

    if result.get('sector_rotation'):
        print(f"Sector Rotation: {result['sector_rotation']}")

    print(f"\n📊 Per-Ticker Technical Analysis:")
    for ticker_analysis in result.get('ticker_analysis', []):
        print(f"\n  {ticker_analysis['ticker']}: "
              f"{ticker_analysis['technical_signal']} "
              f"({ticker_analysis['confidence']}% confidence)")
        print(f"    Trend: {ticker_analysis['trend']}")
        print(f"    RSI: {ticker_analysis['rsi_status']}")
        print(f"    Support: ${ticker_analysis['key_levels']['support']}, "
              f"Resistance: ${ticker_analysis['key_levels']['resistance']}")
        if ticker_analysis.get('patterns'):
            print(f"    Patterns: {', '.join(ticker_analysis['patterns'])}")
        print(f"    Reasoning: {ticker_analysis['reasoning']}")

    print(f"\n💰 Cost: ${llm_router.get_total_cost():.4f}\n")
