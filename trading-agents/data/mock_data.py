"""
Mock Data Generator for MVP Testing
Generates realistic-looking data for testing agent logic
Will be replaced with real APIs in production
"""
from datetime import datetime
from typing import Dict, Any, List
import random

class MockDataGenerator:
    """Generates mock data for testing"""

    def get_portfolio_data(self) -> Dict[str, Any]:
        """
        Generate mock portfolio data from 212 Trading

        Returns:
            Mock portfolio matching 212 API structure
        """
        positions = [
            {
                'ticker': 'AAPL',
                'quantity': 50,
                'avg_cost': 175.00,
                'current_price': 180.25,
                'market_value': 9012.50,
                'unrealized_pnl': 262.50,
                'unrealized_pnl_pct': 3.00
            },
            {
                'ticker': 'TSLA',
                'quantity': 30,
                'avg_cost': 245.00,
                'current_price': 230.50,
                'market_value': 6915.00,
                'unrealized_pnl': -435.00,
                'unrealized_pnl_pct': -5.92
            },
            {
                'ticker': 'MSFT',
                'quantity': 40,
                'avg_cost': 350.00,
                'current_price': 365.75,
                'market_value': 14630.00,
                'unrealized_pnl': 630.00,
                'unrealized_pnl_pct': 4.50
            }
        ]

        total_value = sum(p['market_value'] for p in positions)

        return {
            'positions': positions,
            'total_value': total_value,
            'cash_balance': 2000.00,
            'account_value': total_value + 2000.00,
            'timestamp': datetime.now().isoformat()
        }

    def get_market_overview(self) -> Dict[str, Any]:
        """
        Generate mock market overview data

        Returns:
            Mock market data with indices and sentiment
        """
        # Realistic market scenario: slightly bearish market
        sp500_change = -1.25
        nasdaq_change = -1.80
        vix = 28.5

        return {
            'timestamp': datetime.now().isoformat(),
            'indices': {
                'S&P 500': {
                    'symbol': 'SPY',
                    'price': 450.25,
                    'change': -5.75,
                    'change_pct': sp500_change,
                    'volume': 85000000
                },
                'NASDAQ': {
                    'symbol': 'QQQ',
                    'price': 375.50,
                    'change': -6.90,
                    'change_pct': nasdaq_change,
                    'volume': 45000000
                },
                'VIX': {
                    'symbol': '^VIX',
                    'price': vix,
                    'change': 3.20,
                    'change_pct': 12.67,
                    'volume': 0
                }
            },
            'sentiment_signal': 'BEARISH',  # VIX high, markets down
            'vix_level': vix
        }

    def get_stock_news(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Generate mock news for a stock

        Args:
            ticker: Stock symbol

        Returns:
            List of mock news items
        """
        news_templates = {
            'TSLA': [
                {
                    'headline': 'Tesla recalls 2M vehicles over safety concerns',
                    'summary': 'Tesla announced massive recall affecting 2 million vehicles due to autopilot safety issues.',
                    'source': 'Reuters',
                    'sentiment': 'NEGATIVE',
                    'published_at': '2025-11-17T10:30:00Z'
                },
                {
                    'headline': 'Musk announces new Gigafactory in Texas',
                    'summary': 'Expansion plans revealed for Texas manufacturing capabilities.',
                    'source': 'CNBC',
                    'sentiment': 'POSITIVE',
                    'published_at': '2025-11-17T08:00:00Z'
                }
            ],
            'AAPL': [
                {
                    'headline': 'Apple reports strong iPhone sales in Q4',
                    'summary': 'Apple exceeded expectations with iPhone 15 sales driving revenue growth.',
                    'source': 'Bloomberg',
                    'sentiment': 'POSITIVE',
                    'published_at': '2025-11-17T09:00:00Z'
                }
            ],
            'MSFT': [
                {
                    'headline': 'Microsoft AI cloud revenue surges 35%',
                    'summary': 'Azure AI services driving strong cloud growth for Microsoft.',
                    'source': 'WSJ',
                    'sentiment': 'POSITIVE',
                    'published_at': '2025-11-17T07:00:00Z'
                }
            ]
        }

        return news_templates.get(ticker, [
            {
                'headline': f'{ticker} trading update',
                'summary': f'General market activity for {ticker}',
                'source': 'Market News',
                'sentiment': 'NEUTRAL',
                'published_at': datetime.now().isoformat()
            }
        ])

    def get_technical_indicators(self, ticker: str) -> Dict[str, Any]:
        """
        Generate mock technical indicators

        Args:
            ticker: Stock symbol

        Returns:
            Mock technical data
        """
        # Different scenarios for different tickers
        scenarios = {
            'TSLA': {
                'rsi_14': 35.5,  # Oversold territory
                'macd': {'value': -2.5, 'signal': -1.8, 'histogram': -0.7},
                'ma_50': 245.00,
                'ma_200': 255.00,
                'support': [220.00, 200.00, 180.00],
                'resistance': [250.00, 270.00, 299.00],
                'trend': 'DOWNTREND'
            },
            'AAPL': {
                'rsi_14': 58.0,
                'macd': {'value': 1.2, 'signal': 0.8, 'histogram': 0.4},
                'ma_50': 175.00,
                'ma_200': 170.00,
                'support': [170.00, 165.00, 160.00],
                'resistance': [185.00, 190.00, 200.00],
                'trend': 'UPTREND'
            },
            'MSFT': {
                'rsi_14': 62.0,
                'macd': {'value': 2.0, 'signal': 1.5, 'histogram': 0.5},
                'ma_50': 355.00,
                'ma_200': 345.00,
                'support': [350.00, 340.00, 330.00],
                'resistance': [370.00, 380.00, 400.00],
                'trend': 'UPTREND'
            }
        }

        return scenarios.get(ticker, {
            'rsi_14': 50.0,
            'macd': {'value': 0, 'signal': 0, 'histogram': 0},
            'ma_50': 100.00,
            'ma_200': 100.00,
            'support': [95.00, 90.00, 85.00],
            'resistance': [105.00, 110.00, 115.00],
            'trend': 'SIDEWAYS'
        })


# Test
if __name__ == "__main__":
    generator = MockDataGenerator()
    import json

    print("=== MOCK DATA GENERATOR TEST ===\n")

    print("1. Portfolio Data:")
    portfolio = generator.get_portfolio_data()
    print(json.dumps(portfolio, indent=2))

    print("\n2. Market Overview:")
    market = generator.get_market_overview()
    print(json.dumps(market, indent=2))

    print("\n3. TSLA News:")
    news = generator.get_stock_news('TSLA')
    print(json.dumps(news, indent=2))

    print("\n4. TSLA Technical Indicators:")
    tech = generator.get_technical_indicators('TSLA')
    print(json.dumps(tech, indent=2))

    print("\n✓ Mock data generator working!")
