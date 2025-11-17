"""
Trading 212 API Integration
Fetches real portfolio and account data
"""
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime


class Trading212API:
    """Interface to Trading 212 API"""

    def __init__(self, api_key: str, api_secret: str, mode: str = "live"):
        """
        Initialize Trading 212 API client

        Args:
            api_key: Trading 212 API key ID
            api_secret: Trading 212 API secret key
            mode: "live" or "demo" (default: live)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.mode = mode

        # API endpoints
        if mode == "demo":
            self.base_url = "https://demo.trading212.com/api/v0"
        else:
            self.base_url = "https://live.trading212.com/api/v0"

        # Trading 212 uses API key ID as Authorization header
        self.headers = {
            "Authorization": api_key,
            "X-API-Secret": api_secret,
            "Content-Type": "application/json"
        }

    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information

        Returns:
            Account cash, total value, currency
        """
        url = f"{self.base_url}/equity/account/cash"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def get_portfolio(self) -> List[Dict[str, Any]]:
        """
        Get all open positions

        Returns:
            List of positions with ticker, quantity, avg price, current value, P&L
        """
        url = f"{self.base_url}/equity/portfolio"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def get_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent orders

        Args:
            limit: Number of orders to retrieve

        Returns:
            List of orders
        """
        url = f"{self.base_url}/equity/history/orders"
        params = {"limit": limit}
        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()

        return response.json()

    def get_portfolio_data(self) -> Dict[str, Any]:
        """
        Get formatted portfolio data for agents

        Returns:
            Formatted portfolio data matching agent expectations
        """
        try:
            # Get account and portfolio
            account = self.get_account_info()  # Returns: {free, total, invested, ppl, blocked, pieCash, result}
            positions = self.get_portfolio()    # Returns: [{ticker, quantity, averagePrice, currentPrice, ppl, ...}]

            # Format positions
            formatted_positions = []
            total_value = 0.0

            for pos in positions:
                # Trading 212 response fields: averagePrice, currentPrice, quantity, ppl, ticker
                current_value = pos.get('currentPrice', 0) * pos.get('quantity', 0)
                avg_cost = pos.get('averagePrice', 0)
                quantity = pos.get('quantity', 0)
                invested = avg_cost * quantity

                # ppl field is already the unrealized P&L from Trading 212
                unrealized_pnl = pos.get('ppl', 0)
                unrealized_pnl_pct = (unrealized_pnl / invested * 100) if invested > 0 else 0

                formatted_positions.append({
                    'ticker': pos.get('ticker', ''),
                    'quantity': quantity,
                    'avg_cost': avg_cost,
                    'current_price': pos.get('currentPrice', 0),
                    'market_value': current_value,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': round(unrealized_pnl_pct, 2),
                    'initial_fill_date': pos.get('initialFillDate'),  # ISO 8601 timestamp
                })

                total_value += current_value

            # Account cash fields: free (available), total (account value), invested, ppl (total P&L)
            cash_balance = account.get('free', 0)
            account_value = account.get('total', total_value + cash_balance)  # Use total from API
            total_pnl = account.get('ppl', 0)

            return {
                'positions': formatted_positions,
                'total_value': round(total_value, 2),
                'cash_balance': round(cash_balance, 2),
                'account_value': round(account_value, 2),
                'total_pnl': round(total_pnl, 2),  # Overall account P&L
                'invested': round(account.get('invested', 0), 2),  # Total invested capital
                'blocked': round(account.get('blocked', 0), 2),  # Cash reserved for orders
                'timestamp': datetime.now().isoformat(),
                'source': f'Trading212-{self.mode}'
            }

        except requests.exceptions.HTTPError as e:
            print(f"⚠️  Trading 212 API error: {e}")
            if e.response.status_code == 401:
                print("   Authorization failed - check API key")
            elif e.response.status_code == 403:
                print("   Access forbidden - check API permissions")
            raise
        except Exception as e:
            print(f"⚠️  Error fetching portfolio: {e}")
            raise

    def get_instrument_details(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific instrument

        Args:
            ticker: Stock ticker symbol

        Returns:
            Instrument details
        """
        url = f"{self.base_url}/equity/metadata/instruments"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()

        instruments = response.json()
        for inst in instruments:
            if inst.get('ticker') == ticker:
                return inst

        return None
