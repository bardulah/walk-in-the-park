"""
News Monitor Agent
Analyzes market news and sentiment for portfolio positions
"""
import json
from typing import Dict, Any, List
from utils.json_parser import safe_json_parse


class NewsMonitor:
    """Monitors and analyzes news for trading signals"""

    def __init__(self, llm_router):
        """
        Initialize News Monitor

        Args:
            llm_router: LLM router for model calls
        """
        self.llm_router = llm_router
        self.model = "gemini-flash-or"  # Fast and cheap for news analysis

    def analyze(
        self,
        portfolio_data: Dict[str, Any],
        news_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Analyze news sentiment and impact on portfolio

        Args:
            portfolio_data: Current portfolio positions
            news_data: News articles per ticker

        Returns:
            News analysis with sentiment scores and alerts
        """
        # Get tickers from portfolio
        tickers = [pos['ticker'] for pos in portfolio_data.get('positions', [])]

        system_prompt = """You are a News Analyst specializing in financial news and market sentiment.

Your role is to:
1. Analyze news articles for each stock position
2. Assess sentiment (POSITIVE, NEGATIVE, NEUTRAL) and confidence
3. Identify material news that could impact stock price
4. Flag urgent alerts for significant negative news
5. Provide actionable insights

Output strict JSON format:
{
  "ticker_analysis": [
    {
      "ticker": "AAPL",
      "overall_sentiment": "POSITIVE|NEGATIVE|NEUTRAL",
      "confidence": 0-100,
      "key_themes": ["theme1", "theme2"],
      "material_news": ["summary of important news"],
      "risk_level": "LOW|MEDIUM|HIGH",
      "recommendation": "Brief trading implication"
    }
  ],
  "market_themes": ["Overall market themes from news"],
  "urgent_alerts": ["Any urgent negative news requiring attention"],
  "opportunities": ["Positive catalysts or opportunities identified"]
}"""

        user_prompt = f"""Analyze news for portfolio positions.

Portfolio Tickers: {', '.join(tickers)}

News Data:
{json.dumps(news_data, indent=2)}

Provide comprehensive news analysis focusing on:
- Sentiment and confidence for each position
- Material events (earnings, FDA approvals, lawsuits, management changes)
- Risk assessment
- Trading implications"""

        print(f"🔍 News Monitor analyzing {len(tickers)} positions...")

        try:
            response = self.llm_router.call(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # Lower for factual analysis
                max_tokens=2500,
                json_mode=True
            )

            # Parse JSON response with robust fallback strategies
            fallback = {
                'ticker_analysis': [],
                'market_themes': [],
                'urgent_alerts': [f"News analysis parsing failed"],
                'opportunities': [],
                'agent': 'NewsMonitor',
                'fallback': True
            }

            analysis = safe_json_parse(response, default=fallback)

            # Add metadata
            analysis['agent'] = 'NewsMonitor'
            analysis['model_used'] = self.model

            print(f"   ✓ Analysis complete")
            print(f"   Urgent Alerts: {len(analysis.get('urgent_alerts', []))}")
            print(f"   Opportunities: {len(analysis.get('opportunities', []))}")

            return analysis

        except Exception as e:
            print(f"   ❌ News analysis failed: {e}")
            return {
                'ticker_analysis': [],
                'market_themes': [],
                'urgent_alerts': [f"News analysis failed: {str(e)}"],
                'opportunities': [],
                'agent': 'NewsMonitor',
                'error': str(e)
            }


if __name__ == "__main__":
    # Test News Monitor
    from config.llm_router_unified import UnifiedLLMRouter
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*60)
    print("  NEWS MONITOR AGENT - TEST")
    print("="*60 + "\n")

    # Initialize
    llm_router = UnifiedLLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )

    news_monitor = NewsMonitor(llm_router)
    mock_data = MockDataGenerator()

    # Get test data
    portfolio = mock_data.get_portfolio_data()

    # Get news for each ticker
    news_data = {}
    for pos in portfolio['positions']:
        ticker = pos['ticker']
        news_data[ticker] = mock_data.get_stock_news(ticker)

    # Run analysis
    result = news_monitor.analyze(portfolio, news_data)

    # Display results
    print("\n📰 NEWS ANALYSIS:")
    print(f"\nMarket Themes: {len(result.get('market_themes', []))}")
    for theme in result.get('market_themes', []):
        print(f"  - {theme}")

    print(f"\n⚠️  Urgent Alerts: {len(result.get('urgent_alerts', []))}")
    for alert in result.get('urgent_alerts', []):
        print(f"  ! {alert}")

    print(f"\n💡 Opportunities: {len(result.get('opportunities', []))}")
    for opp in result.get('opportunities', []):
        print(f"  + {opp}")

    print(f"\n📊 Per-Ticker Analysis:")
    for ticker_analysis in result.get('ticker_analysis', []):
        print(f"\n  {ticker_analysis['ticker']}: "
              f"{ticker_analysis['overall_sentiment']} "
              f"({ticker_analysis['confidence']}% confidence)")
        print(f"    Risk: {ticker_analysis['risk_level']}")
        print(f"    Recommendation: {ticker_analysis['recommendation']}")

    print(f"\n💰 Cost: ${llm_router.get_total_cost():.4f}\n")
