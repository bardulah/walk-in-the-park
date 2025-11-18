"""
Trading Safety System
Critical safety checks to prevent catastrophic losses in live trading
"""
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from enum import Enum
from config.logging_config import get_logger


logger = get_logger("trading_safety")


class SafetyViolation(Exception):
    """Raised when a safety check fails"""
    pass


class KillSwitchStatus(Enum):
    """Kill switch states"""
    ACTIVE = "active"      # Trading allowed
    TRIGGERED = "triggered"  # Trading halted
    MANUAL_OVERRIDE = "manual_override"  # Temporarily bypassed


class TradingSafetySystem:
    """
    Comprehensive trading safety system

    Prevents catastrophic losses through multiple safety layers:
    1. Position size limits (max % of portfolio)
    2. Sector concentration limits
    3. Daily loss limits (circuit breaker)
    4. Account balance validation
    5. Manual approval for large trades
    6. Emergency kill switch
    7. Position reconciliation

    Usage:
        safety = TradingSafetySystem(
            max_position_pct=25.0,
            max_daily_loss_pct=5.0,
            large_trade_threshold=10000.0
        )

        # Before placing order
        safety.validate_trade(
            ticker='AAPL',
            quantity=100,
            price=150.0,
            action='buy',
            account=account_info,
            portfolio=current_portfolio
        )

        # Emergency stop
        safety.trigger_kill_switch("Market crash detected")
    """

    def __init__(
        self,
        max_position_pct: float = 25.0,
        max_sector_concentration_pct: float = 50.0,
        max_daily_loss_pct: float = 5.0,
        max_daily_loss_amount: Optional[float] = None,
        large_trade_threshold: float = 10000.0,
        enable_kill_switch: bool = True,
        require_approval_for_large_trades: bool = True
    ):
        """
        Initialize trading safety system

        Args:
            max_position_pct: Maximum position size as % of portfolio (default: 25%)
            max_sector_concentration_pct: Maximum sector exposure (default: 50%)
            max_daily_loss_pct: Maximum daily loss % before halting (default: 5%)
            max_daily_loss_amount: Maximum daily loss $ (optional)
            large_trade_threshold: Trade size requiring approval (default: $10,000)
            enable_kill_switch: Enable emergency kill switch
            require_approval_for_large_trades: Require manual approval for large trades
        """
        self.max_position_pct = max_position_pct
        self.max_sector_concentration_pct = max_sector_concentration_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_daily_loss_amount = max_daily_loss_amount
        self.large_trade_threshold = large_trade_threshold
        self.enable_kill_switch = enable_kill_switch
        self.require_approval_for_large_trades = require_approval_for_large_trades

        self.logger = logger

        # Kill switch state
        self.kill_switch_status = KillSwitchStatus.ACTIVE
        self.kill_switch_reason = None
        self.kill_switch_time = None

        # Daily tracking
        self.daily_start_value = None
        self.daily_trades = []
        self.daily_pnl = 0.0
        self.last_reset_date = date.today()

        # Pending approvals
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

        self.logger.info(
            f"TradingSafetySystem initialized | "
            f"Max position: {max_position_pct}% | "
            f"Max daily loss: {max_daily_loss_pct}% | "
            f"Large trade threshold: ${large_trade_threshold:,.0f}"
        )

    def validate_trade(
        self,
        ticker: str,
        quantity: float,
        price: float,
        action: str,
        account: Dict[str, Any],
        portfolio: Optional[Dict[str, Any]] = None,
        sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate trade against all safety rules

        Args:
            ticker: Stock ticker
            quantity: Number of shares
            price: Price per share
            action: 'buy' or 'sell'
            account: Account information (cash, total_value)
            portfolio: Current portfolio positions
            sector: Stock sector (for concentration limits)

        Returns:
            Dict with validation result

        Raises:
            SafetyViolation: If any safety check fails
        """
        self._reset_daily_tracking_if_needed()

        trade_value = quantity * price

        self.logger.info(
            f"Validating trade: {action.upper()} {quantity} {ticker} @ ${price:.2f} "
            f"(${trade_value:,.2f})"
        )

        # Check 1: Kill switch
        self._check_kill_switch()

        # Check 2: Account balance
        if action.lower() == 'buy':
            self._check_account_balance(trade_value, account)

        # Check 3: Position size limits
        if action.lower() == 'buy' and portfolio:
            self._check_position_size(ticker, trade_value, account, portfolio)

        # Check 4: Sector concentration
        if action.lower() == 'buy' and portfolio and sector:
            self._check_sector_concentration(sector, trade_value, account, portfolio)

        # Check 5: Daily loss limits
        self._check_daily_loss_limits(account)

        # Check 6: Large trade approval
        if trade_value > self.large_trade_threshold and self.require_approval_for_large_trades:
            approval_needed = self._require_approval(ticker, quantity, price, action, trade_value)

            if not approval_needed['approved']:
                raise SafetyViolation(
                    f"Large trade requires manual approval: ${trade_value:,.2f} > ${self.large_trade_threshold:,.2f}"
                )

        self.logger.info(f"✅ Trade validation passed for {ticker}")

        return {
            'validated': True,
            'trade_value': trade_value,
            'checks_passed': [
                'kill_switch',
                'account_balance',
                'position_size',
                'sector_concentration',
                'daily_loss_limits',
                'large_trade_approval'
            ]
        }

    def _check_kill_switch(self):
        """Check if kill switch is active"""
        if not self.enable_kill_switch:
            return

        if self.kill_switch_status == KillSwitchStatus.TRIGGERED:
            raise SafetyViolation(
                f"❌ KILL SWITCH ACTIVATED: {self.kill_switch_reason} | "
                f"Activated at: {self.kill_switch_time}"
            )

    def _check_account_balance(self, trade_value: float, account: Dict[str, Any]):
        """Check sufficient funds for trade"""
        cash_available = account.get('cash', 0)

        if trade_value > cash_available:
            raise SafetyViolation(
                f"Insufficient funds: ${trade_value:,.2f} > ${cash_available:,.2f}"
            )

        # Warn if using >90% of cash
        if trade_value > cash_available * 0.9:
            self.logger.warning(
                f"⚠️  Trade uses {(trade_value/cash_available)*100:.1f}% of available cash"
            )

    def _check_position_size(
        self,
        ticker: str,
        trade_value: float,
        account: Dict[str, Any],
        portfolio: Dict[str, Any]
    ):
        """Check position size limits"""
        total_portfolio_value = account.get('total_value', account.get('cash', 0))

        # Get current position value
        current_positions = portfolio.get('positions', [])
        current_position_value = 0.0

        for position in current_positions:
            if position.get('ticker') == ticker:
                current_position_value = position.get('market_value', 0)
                break

        # Calculate new position value
        new_position_value = current_position_value + trade_value

        # Check if exceeds limit
        position_pct = (new_position_value / total_portfolio_value) * 100

        if position_pct > self.max_position_pct:
            raise SafetyViolation(
                f"Position size limit exceeded for {ticker}: {position_pct:.1f}% > "
                f"{self.max_position_pct:.1f}% | "
                f"New position would be: ${new_position_value:,.2f}"
            )

        if position_pct > self.max_position_pct * 0.8:
            self.logger.warning(
                f"⚠️  {ticker} position approaching limit: {position_pct:.1f}% of "
                f"{self.max_position_pct:.1f}%"
            )

    def _check_sector_concentration(
        self,
        sector: str,
        trade_value: float,
        account: Dict[str, Any],
        portfolio: Dict[str, Any]
    ):
        """Check sector concentration limits"""
        total_portfolio_value = account.get('total_value', account.get('cash', 0))

        # Calculate current sector exposure
        current_positions = portfolio.get('positions', [])
        sector_exposure = 0.0

        for position in current_positions:
            if position.get('sector') == sector:
                sector_exposure += position.get('market_value', 0)

        # Add new trade
        new_sector_exposure = sector_exposure + trade_value
        sector_pct = (new_sector_exposure / total_portfolio_value) * 100

        if sector_pct > self.max_sector_concentration_pct:
            raise SafetyViolation(
                f"Sector concentration limit exceeded for {sector}: {sector_pct:.1f}% > "
                f"{self.max_sector_concentration_pct:.1f}% | "
                f"Sector exposure would be: ${new_sector_exposure:,.2f}"
            )

    def _check_daily_loss_limits(self, account: Dict[str, Any]):
        """Check daily loss limits (circuit breaker)"""
        if self.daily_start_value is None:
            self.daily_start_value = account.get('total_value', 0)
            self.logger.info(f"Daily start value: ${self.daily_start_value:,.2f}")

        current_value = account.get('total_value', 0)
        daily_pnl = current_value - self.daily_start_value
        daily_pnl_pct = (daily_pnl / self.daily_start_value) * 100

        # Check percentage limit
        if daily_pnl_pct < -self.max_daily_loss_pct:
            self.trigger_kill_switch(
                f"Daily loss limit exceeded: {daily_pnl_pct:.2f}% < -{self.max_daily_loss_pct:.2f}%"
            )
            raise SafetyViolation(
                f"CIRCUIT BREAKER: Daily loss {daily_pnl_pct:.2f}% exceeds limit "
                f"-{self.max_daily_loss_pct:.2f}%"
            )

        # Check dollar limit if set
        if self.max_daily_loss_amount and daily_pnl < -self.max_daily_loss_amount:
            self.trigger_kill_switch(
                f"Daily loss amount exceeded: ${daily_pnl:,.2f} < -${self.max_daily_loss_amount:,.2f}"
            )
            raise SafetyViolation(
                f"CIRCUIT BREAKER: Daily loss ${-daily_pnl:,.2f} exceeds limit "
                f"${self.max_daily_loss_amount:,.2f}"
            )

        # Warn at 80% of limit
        if daily_pnl_pct < -self.max_daily_loss_pct * 0.8:
            self.logger.warning(
                f"⚠️  Daily loss approaching limit: {daily_pnl_pct:.2f}% "
                f"(limit: -{self.max_daily_loss_pct:.2f}%)"
            )

    def _require_approval(
        self,
        ticker: str,
        quantity: float,
        price: float,
        action: str,
        trade_value: float
    ) -> Dict[str, Any]:
        """
        Require manual approval for large trades

        In production, this would integrate with a manual approval system.
        For now, it logs and creates a pending approval.
        """
        import uuid

        approval_id = str(uuid.uuid4())[:8]

        approval_request = {
            'approval_id': approval_id,
            'ticker': ticker,
            'quantity': quantity,
            'price': price,
            'action': action,
            'trade_value': trade_value,
            'timestamp': datetime.now().isoformat(),
            'approved': False  # Requires manual approval
        }

        self.pending_approvals[approval_id] = approval_request

        self.logger.warning(
            f"⚠️  APPROVAL REQUIRED | ID: {approval_id} | "
            f"{action.upper()} {quantity} {ticker} @ ${price:.2f} (${trade_value:,.2f})"
        )

        return approval_request

    def approve_trade(self, approval_id: str, approved: bool, reason: str = ""):
        """
        Approve or reject pending trade

        Args:
            approval_id: Approval request ID
            approved: True to approve, False to reject
            reason: Approval/rejection reason
        """
        if approval_id not in self.pending_approvals:
            raise ValueError(f"Unknown approval ID: {approval_id}")

        approval = self.pending_approvals[approval_id]
        approval['approved'] = approved
        approval['approval_reason'] = reason
        approval['approval_time'] = datetime.now().isoformat()

        status = "APPROVED" if approved else "REJECTED"
        self.logger.info(
            f"Trade {status} | ID: {approval_id} | Reason: {reason}"
        )

    def trigger_kill_switch(self, reason: str):
        """
        Trigger emergency kill switch - halts all trading

        Args:
            reason: Reason for triggering kill switch
        """
        self.kill_switch_status = KillSwitchStatus.TRIGGERED
        self.kill_switch_reason = reason
        self.kill_switch_time = datetime.now()

        self.logger.critical(
            f"🚨 KILL SWITCH ACTIVATED 🚨 | Reason: {reason} | "
            f"Time: {self.kill_switch_time.isoformat()}"
        )

    def reset_kill_switch(self, override_reason: str):
        """
        Reset kill switch (use with caution!)

        Args:
            override_reason: Reason for resetting
        """
        if self.kill_switch_status != KillSwitchStatus.TRIGGERED:
            self.logger.warning("Kill switch not triggered - no need to reset")
            return

        self.kill_switch_status = KillSwitchStatus.ACTIVE
        previous_reason = self.kill_switch_reason
        self.kill_switch_reason = None
        self.kill_switch_time = None

        self.logger.warning(
            f"⚠️  Kill switch RESET | Previous reason: {previous_reason} | "
            f"Override reason: {override_reason}"
        )

    def _reset_daily_tracking_if_needed(self):
        """Reset daily tracking at start of new day"""
        today = date.today()

        if today > self.last_reset_date:
            self.logger.info(
                f"New trading day - resetting daily tracking | "
                f"Previous P&L: ${self.daily_pnl:,.2f}"
            )

            self.daily_start_value = None
            self.daily_trades = []
            self.daily_pnl = 0.0
            self.last_reset_date = today

    def record_trade(
        self,
        ticker: str,
        quantity: float,
        price: float,
        action: str,
        execution_time: Optional[datetime] = None
    ):
        """Record executed trade for tracking"""
        trade_record = {
            'ticker': ticker,
            'quantity': quantity,
            'price': price,
            'action': action,
            'value': quantity * price,
            'timestamp': execution_time or datetime.now()
        }

        self.daily_trades.append(trade_record)

        self.logger.info(
            f"Trade recorded: {action.upper()} {quantity} {ticker} @ ${price:.2f}"
        )

    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety status"""
        return {
            'kill_switch': {
                'status': self.kill_switch_status.value,
                'reason': self.kill_switch_reason,
                'triggered_at': self.kill_switch_time.isoformat() if self.kill_switch_time else None
            },
            'daily_tracking': {
                'start_value': self.daily_start_value,
                'current_pnl': self.daily_pnl,
                'trades_today': len(self.daily_trades),
                'last_reset': self.last_reset_date.isoformat()
            },
            'limits': {
                'max_position_pct': self.max_position_pct,
                'max_sector_concentration_pct': self.max_sector_concentration_pct,
                'max_daily_loss_pct': self.max_daily_loss_pct,
                'max_daily_loss_amount': self.max_daily_loss_amount,
                'large_trade_threshold': self.large_trade_threshold
            },
            'pending_approvals': len(self.pending_approvals)
        }

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests"""
        return [
            approval for approval in self.pending_approvals.values()
            if not approval['approved']
        ]
