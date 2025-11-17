"""
Stock Screener Agent
Identifies new stock opportunities based on market conditions and portfolio needs
"""
import json
from typing import Dict, Any, List


class StockScreener:
    """Screens for new stock opportunities"""

    def __init__(self, llm_router):
        """
        Initialize Stock Screener

        Args:
            llm_router: LLM router for model calls
        """
        self.llm_router = llm_router
        self.model = "gpt-4o-mini"  # Fast model for screening

    def screen(
        self,
        portfolio_data: Dict[str, Any],
        market_analysis: Dict[str, Any],
        news_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Screen for new stock opportunities

        Args:
            portfolio_data: Current portfolio positions
            market_analysis: Market sentiment and sector trends
            news_analysis: News themes and opportunities

        Returns:
            New stock recommendations
        """
        system_prompt = """You are a Stock Screener specializing in identifying investment opportunities.

Your role:
1. Identify stocks that complement current portfolio
2. Find opportunities aligned with market trends
3. Suggest diversification plays
4. Recommend both growth and defensive stocks
5. Consider sector rotation patterns

Output strict JSON format:
{
  "buy_opportunities": [
    {
      "ticker": "NVDA",
      "category": "GROWTH|VALUE|DEFENSIVE|DIVIDEND",
      "sector": "Technology|Healthcare|Energy|etc",
      "confidence": 0-100,
      "entry_range": {"low": 450.00, "high": 465.00},
      "target_price": 550.00,
      "stop_loss": 420.00,
      "position_size_pct": 5-15,
      "timeframe": "1-3_MONTHS|3-6_MONTHS|6-12_MONTHS",
      "reasoning": "Clear fundamental/technical/news-driven rationale",
      "catalysts": ["Upcoming earnings", "Product launch", "Sector rotation"]
    }
  ],
  "sector_allocation": {
    "recommended_sectors": ["Utilities", "Healthcare"],
    "avoid_sectors": ["Technology"],
    "rationale": "Defensive rotation during bearish market"
  },
  "diversification_needs": ["Need defensive stocks", "Reduce tech concentration"],
  "top_picks": ["Top 3 tickers with highest conviction"]
}"""

        # Get current portfolio composition
        tickers = [pos['ticker'] for pos in portfolio_data.get('positions', [])]

        # Calculate sector exposure (simplified)
        sector_map = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'TSLA': 'Technology', 'NVDA': 'Technology', 'AMD': 'Technology',
            'JPM': 'Financials', 'BAC': 'Financials', 'GS': 'Financials',
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
            'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
            'WMT': 'Consumer Staples', 'PG': 'Consumer Staples', 'KO': 'Consumer Staples',
            'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities'
        }

        current_sectors = [sector_map.get(t.split('_')[0], 'Unknown') for t in tickers]

        user_prompt = f"""Screen for new stock opportunities to complement current portfolio.

CURRENT PORTFOLIO:
Positions: {len(portfolio_data.get('positions', []))}
Tickers: {', '.join(tickers)}
Current Sectors: {', '.join(set(current_sectors))}
Account Value: ${portfolio_data.get('account_value', 0):,.2f}
Cash Available: ${portfolio_data.get('cash_balance', 0):,.2f}

MARKET CONDITIONS:
Sentiment: {market_analysis.get('sentiment', 'N/A')}
Volatility: {market_analysis.get('volatility_assessment', 'N/A')}
Sector Trends: {json.dumps(market_analysis.get('sector_trends', []))}

NEWS THEMES:
Opportunities: {json.dumps(news_analysis.get('opportunities', [])[:3])}
Market Themes: {json.dumps(news_analysis.get('market_themes', []))}

SCREENING CRITERIA:
1. Identify 3-5 high-conviction BUY opportunities
2. Prioritize diversification (avoid over-concentrated sectors)
3. Mix of growth, value, and defensive stocks
4. Consider market conditions (bearish = more defensive)
5. Provide specific entry ranges and targets
6. Position sizing: 5-15% of portfolio per stock

Generate actionable buy recommendations with clear rationale."""

        print(f"🔍 Stock Screener analyzing opportunities...")

        try:
            response = self.llm_router.call(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.6,
                max_tokens=2500,
                json_mode=True
            )

            analysis = json.loads(response)

            # Add metadata
            analysis['agent'] = 'StockScreener'
            analysis['model_used'] = self.model

            print(f"   ✓ Screened opportunities")
            print(f"   Buy Opportunities: {len(analysis.get('buy_opportunities', []))}")

            return analysis

        except Exception as e:
            print(f"   ❌ Screening failed: {e}")
            return {
                'buy_opportunities': [],
                'sector_allocation': {},
                'diversification_needs': [],
                'top_picks': [],
                'agent': 'StockScreener',
                'error': str(e)
            }


if __name__ == "__main__":
    # Test Stock Screener
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

    from config.llm_router_unified import UnifiedLLMRouter
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*60)
    print("  STOCK SCREENER AGENT - TEST")
    print("="*60 + "\n")

    # Initialize
    llm_router = UnifiedLLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )

    screener = StockScreener(llm_router)
    mock_data = MockDataGenerator()

    # Get test data
    portfolio = mock_data.get_portfolio_data()
    market = mock_data.get_market_overview()

    # Mock news analysis
    news_analysis = {
        'opportunities': ['Utilities sector showing strength', 'Healthcare defensive play'],
        'market_themes': ['Defensive rotation', 'Risk-off sentiment']
    }

    # Mock market analysis
    market_analysis = {
        'sentiment': 'BEARISH',
        'volatility_assessment': 'HIGH',
        'sector_trends': ['Technology underperforming', 'Utilities outperforming']
    }

    # Run screening
    result = screener.screen(portfolio, market_analysis, news_analysis)

    # Display results
    print("\n🔍 STOCK SCREENING RESULTS:")

    print(f"\n💡 BUY OPPORTUNITIES ({len(result.get('buy_opportunities', []))}):")
    for i, opp in enumerate(result.get('buy_opportunities', []), 1):
        print(f"\n{i}. {opp['ticker']} - {opp['category']}")
        print(f"   Sector: {opp['sector']}")
        print(f"   Confidence: {opp['confidence']}%")
        print(f"   Entry: ${opp['entry_range']['low']:.2f} - ${opp['entry_range']['high']:.2f}")
        print(f"   Target: ${opp['target_price']:.2f} | Stop: ${opp['stop_loss']:.2f}")
        print(f"   Position Size: {opp['position_size_pct']}% of portfolio")
        print(f"   Timeframe: {opp['timeframe']}")
        print(f"   Reasoning: {opp['reasoning'][:100]}...")

    print(f"\n📊 SECTOR ALLOCATION:")
    sector_alloc = result.get('sector_allocation', {})
    if sector_alloc.get('recommended_sectors'):
        print(f"   Recommended: {', '.join(sector_alloc['recommended_sectors'])}")
    if sector_alloc.get('avoid_sectors'):
        print(f"   Avoid: {', '.join(sector_alloc['avoid_sectors'])}")
    if sector_alloc.get('rationale'):
        print(f"   Rationale: {sector_alloc['rationale']}")

    print(f"\n🎯 TOP PICKS: {', '.join(result.get('top_picks', []))}")

    print(f"\n💰 Cost: ${llm_router.get_total_cost():.4f}\n")
