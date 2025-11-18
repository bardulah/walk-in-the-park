"""Trading 212 API data models"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """Order types supported by Trading 212"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderAction(Enum):
    """Order actions"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TimeInForce(Enum):
    """Time in force options"""
    DAY = "day"
    GTC = "gtc"  # Good till cancelled


@dataclass
class OrderRequest:
    """Request to place an order"""
    ticker: str
    action: OrderAction
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY

    def to_api_params(self) -> dict:
        """Convert to Trading 212 API parameters"""
        # Trading 212 uses negative quantity for sells
        api_quantity = self.quantity if self.action == OrderAction.BUY else -abs(self.quantity)

        params = {
            'ticker': self.ticker,
            'quantity': api_quantity,
        }

        if self.limit_price is not None:
            params['limitPrice'] = self.limit_price

        if self.stop_price is not None:
            params['stopPrice'] = self.stop_price

        if self.time_in_force != TimeInForce.DAY:
            params['timeValidity'] = self.time_in_force.value.upper()

        return params


@dataclass
class Order:
    """Order information"""
    order_id: str
    ticker: str
    action: OrderAction
    quantity: float
    order_type: OrderType
    status: OrderStatus
    filled_quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    average_fill_price: Optional[float] = None

    @classmethod
    def from_api_response(cls, data: dict) -> 'Order':
        """Create Order from API response"""
        # Parse action from quantity sign
        quantity = data.get('quantity', 0)
        action = OrderAction.BUY if quantity > 0 else OrderAction.SELL

        return cls(
            order_id=data.get('id'),
            ticker=data.get('ticker'),
            action=action,
            quantity=abs(quantity),
            order_type=OrderType(data.get('type', 'market').lower()),
            status=OrderStatus(data.get('status', 'pending').lower()),
            filled_quantity=abs(data.get('filledQuantity', 0)),
            limit_price=data.get('limitPrice'),
            stop_price=data.get('stopPrice'),
            created_at=cls._parse_datetime(data.get('createdAt')),
            filled_at=cls._parse_datetime(data.get('filledAt')),
            average_fill_price=data.get('fillPrice')
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if dt_str is None:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None


@dataclass
class Position:
    """Current position"""
    ticker: str
    quantity: float
    average_price: float
    current_price: float
    market_value: float
    pnl: float
    pnl_pct: float

    @classmethod
    def from_api_response(cls, data: dict) -> 'Position':
        """Create Position from API response"""
        quantity = data.get('quantity', 0)
        avg_price = data.get('averagePrice', 0)
        current_price = data.get('currentPrice', 0)
        market_value = quantity * current_price
        pnl = market_value - (quantity * avg_price)
        pnl_pct = (pnl / (quantity * avg_price) * 100) if avg_price > 0 else 0

        return cls(
            ticker=data.get('ticker'),
            quantity=quantity,
            average_price=avg_price,
            current_price=current_price,
            market_value=market_value,
            pnl=pnl,
            pnl_pct=pnl_pct
        )


@dataclass
class Account:
    """Account information"""
    cash: float
    total_value: float
    pnl: float
    blocked_funds: float

    @classmethod
    def from_api_response(cls, data: dict) -> 'Account':
        """Create Account from API response"""
        return cls(
            cash=data.get('cash', 0),
            total_value=data.get('total', 0),
            pnl=data.get('ppl', 0),  # profit/loss
            blocked_funds=data.get('blocked', 0)
        )
