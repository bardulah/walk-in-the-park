"""
Hybrid Data Fetcher
Tries real APIs first, falls back to mock data if unavailable
"""
from typing import Dict, Any
from data.trading212_api import Trading212API
from data.mock_data import MockDataGenerator


class HybridDataFetcher:
    """Fetches data from real APIs with mock fallback"""

    def __init__(self, trading_212_api_key: str, trading_212_api_secret: str, use_mock: bool = False):
        """
        Initialize hybrid fetcher

        Args:
            trading_212_api_key: Trading 212 API key ID
            trading_212_api_secret: Trading 212 API secret key
            use_mock: Force mock data (for testing)
        """
        self.use_mock = use_mock
        self.trading_api = None
        self.mock_data = MockDataGenerator()

        if not use_mock and trading_212_api_key and trading_212_api_secret:
            try:
                self.trading_api = Trading212API(trading_212_api_key, trading_212_api_secret, mode='live')
            except Exception as e:
                print(f"⚠️  Trading 212 API initialization failed: {e}")

    def get_portfolio_data(self) -> Dict[str, Any]:
        """Get portfolio data (real or mock)"""
        if self.use_mock or not self.trading_api:
            return self.mock_data.get_portfolio_data()

        try:
            return self.trading_api.get_portfolio_data()
        except Exception as e:
            print(f"⚠️  Falling back to mock portfolio data: {e}")
            return self.mock_data.get_portfolio_data()

    def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview (mock for now)"""
        return self.mock_data.get_market_overview()

    def get_stock_news(self, ticker: str) -> list:
        """Get stock news (mock for now)"""
        return self.mock_data.get_stock_news(ticker)
