"""
Market Data Fetcher - Tier 1 (FREE sources)
Fetches market data from Yahoo Finance and other free APIs
"""
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

class MarketDataFetcher:
    """Fetches market data from free sources"""

    def __init__(self):
        """Initialize market data fetcher"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; TradingBot/1.0)'
        })

    def get_market_overview(self) -> Dict[str, Any]:
        """
        Get current market overview (indices, VIX)

        Returns:
            Dict with market data
        """
        try:
            # Fetch major indices from Yahoo Finance
            symbols = {
                'SPY': 'S&P 500',
                'QQQ': 'NASDAQ',
                '^VIX': 'VIX'
            }

            market_data = {}

            for symbol, name in symbols.items():
                try:
                    data = self._fetch_yahoo_quote(symbol)
                    market_data[name] = {
                        'symbol': symbol,
                        'price': data.get('regularMarketPrice', 0),
                        'change': data.get('regularMarketChange', 0),
                        'change_pct': data.get('regularMarketChangePercent', 0),
                        'volume': data.get('regularMarketVolume', 0)
                    }
                except Exception as e:
                    print(f"  ⚠️  Failed to fetch {symbol}: {e}")
                    market_data[name] = self._get_fallback_data(symbol)

            # Calculate market sentiment
            sp500_change = market_data.get('S&P 500', {}).get('change_pct', 0)
            vix_value = market_data.get('VIX', {}).get('price', 20)

            sentiment = "NEUTRAL"
            if sp500_change > 1.0 and vix_value < 20:
                sentiment = "BULLISH"
            elif sp500_change < -1.0 or vix_value > 30:
                sentiment = "BEARISH"

            return {
                'timestamp': datetime.now().isoformat(),
                'indices': market_data,
                'sentiment_signal': sentiment,
                'vix_level': vix_value
            }

        except Exception as e:
            print(f"⚠️  Market data fetch failed: {e}")
            return self._get_fallback_market_data()

    def _fetch_yahoo_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch quote from Yahoo Finance API"""
        # Using Yahoo Finance v7 API (free, no auth required)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"

        response = self.session.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        if 'quoteResponse' in data and 'result' in data['quoteResponse']:
            results = data['quoteResponse']['result']
            if results:
                return results[0]

        raise ValueError(f"No data returned for {symbol}")

    def get_stock_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get quote for specific stock

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with stock data
        """
        try:
            data = self._fetch_yahoo_quote(ticker)
            return {
                'ticker': ticker,
                'price': data.get('regularMarketPrice', 0),
                'change_pct': data.get('regularMarketChangePercent', 0),
                '52w_high': data.get('fiftyTwoWeekHigh', 0),
                '52w_low': data.get('fiftyTwoWeekLow', 0),
                'volume': data.get('regularMarketVolume', 0),
                'avg_volume': data.get('averageDailyVolume10Day', 0),
                'market_cap': data.get('marketCap', 0),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"⚠️  Failed to fetch quote for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}

    def _get_fallback_data(self, symbol: str) -> Dict[str, Any]:
        """Fallback data if API fails"""
        return {
            'symbol': symbol,
            'price': 0,
            'change': 0,
            'change_pct': 0,
            'volume': 0,
            'error': 'API unavailable'
        }

    def _get_fallback_market_data(self) -> Dict[str, Any]:
        """Fallback market data if all fails"""
        return {
            'timestamp': datetime.now().isoformat(),
            'indices': {
                'S&P 500': self._get_fallback_data('SPY'),
                'NASDAQ': self._get_fallback_data('QQQ'),
                'VIX': self._get_fallback_data('^VIX')
            },
            'sentiment_signal': 'NEUTRAL',
            'vix_level': 20,
            'error': 'Market data unavailable - using fallback'
        }


# Test function
if __name__ == "__main__":
    fetcher = MarketDataFetcher()
    print("Testing Market Data Fetcher...")
    print("\n1. Market Overview:")
    overview = fetcher.get_market_overview()
    import json
    print(json.dumps(overview, indent=2))

    print("\n2. Stock Quote (AAPL):")
    quote = fetcher.get_stock_quote("AAPL")
    print(json.dumps(quote, indent=2))
