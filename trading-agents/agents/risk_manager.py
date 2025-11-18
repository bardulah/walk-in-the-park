"""
Risk Manager Agent
Enforces risk limits and has override authority on all recommendations
"""
import json
from typing import Dict, Any, List
from utils.json_parser import safe_json_parse
from agents.base_agent import BaseAgent

# System prompt for Risk Manager
RISK_MANAGER_SYSTEM_PROMPT = """You are a Risk Manager with FINAL AUTHORITY over all trading decisions.

Your PRIMARY responsibility is to PROTECT capital and enforce risk limits.

You have the power to:
1. VETO any recommendation that violates risk limits
2. OVERRIDE other agents if risk is too high
3. FORCE position reductions when limits are breached
4. HALT trading when market conditions are too volatile

Risk Limits to Enforce:
- Max single position: 25% of portfolio
- Max sector concentration: 50% of portfolio
- Max position loss: -10% (force sell)
- Max portfolio drawdown: -15% (defensive mode)
- Min cash reserve: 5% of account value
- VIX >30: Reduce risk, increase cash

Your Mandate:
- Capital preservation > profit maximization
- Be conservative in high volatility
- Reject aggressive recommendations during uncertain markets
- Flag concentrations risks immediately
- Never allow violations of hard limits

Output strict JSON format:
{
  "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
  "portfolio_health": 0-100,
  "current_violations": ["List any active risk violations"],
  "approved_recommendations": [
    {
      "ticker": "AAPL",
      "action": "REDUCE",
      "priority": "HIGH",
      "confidence": 85,
      "reasoning": "Approved: concentration risk",
      "approved_by_risk_manager": true
    }
  ],
  "rejected_recommendations": [
    {
      "ticker": "TSLA",
      "action": "BUY",
      "rejection_reason": "Would exceed sector concentration limit",
      "approved_by_risk_manager": false
    }
  ],
  "forced_actions": [
    {
      "ticker": "NVDA",
      "action": "REDUCE",
      "reason": "Position exceeds 25% limit",
      "target_size_pct": 20.0
    }
  ],
  "risk_warnings": ["List of risk warnings"],
  "reasoning": "Overall risk assessment and key decisions"
}"""


class RiskManager(BaseAgent):
    """Manages portfolio risk and has final override authority"""

    def __init__(self, llm_router, risk_config: Dict[str, Any] = None):
        """
        Initialize Risk Manager

        Args:
            llm_router: LLM router for model calls
            risk_config: Risk parameters (position limits, loss limits, etc.)
        """
        super().__init__(
            llm_router=llm_router,
            model="claude-3-5-sonnet",  # Use best model for critical risk decisions
            temperature=0.2,  # Very low for consistent risk enforcement
            max_tokens=3000,
            agent_name="Risk Manager"
        )

        # Default risk configuration
        self.risk_config = risk_config or {
            'max_position_size_pct': 25.0,  # Max 25% in single position
            'max_sector_concentration_pct': 50.0,  # Max 50% in single sector
            'max_portfolio_loss_pct': 15.0,  # Stop if down 15% from peak
            'max_single_position_loss_pct': 10.0,  # Stop single position at -10%
            'min_cash_reserve_pct': 5.0,  # Maintain 5% cash
            'max_daily_trades': 10,  # Max 10 trades per day
            'vix_threshold': 30.0,  # Reduce risk if VIX > 30
        }

    def get_system_prompt(self) -> str:
        """Get system prompt for Risk Manager"""
        return RISK_MANAGER_SYSTEM_PROMPT

    def analyze(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
        all_recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate portfolio risk and override recommendations if needed

        Args:
            portfolio_data: Current portfolio positions
            market_data: Market conditions
            all_recommendations: Recommendations from all agents

        Returns:
            Risk assessment with approved/rejected recommendations
        """
        self._log_progress("evaluating portfolio risk...", emoji="⚠️")

        # Calculate current risk metrics
        total_value = portfolio_data.get('total_value', 0)
        account_value = portfolio_data.get('account_value', 1)
        cash_pct = (portfolio_data.get('cash_balance', 0) / account_value * 100) if account_value > 0 else 0

        # Position concentration
        positions = portfolio_data.get('positions', [])
        position_concentrations = []
        for pos in positions:
            pct = (pos['market_value'] / account_value * 100) if account_value > 0 else 0
            position_concentrations.append({
                'ticker': pos['ticker'],
                'concentration_pct': round(pct, 2),
                'unrealized_pnl_pct': pos['unrealized_pnl_pct']
            })

        user_prompt = f"""Evaluate portfolio risk and approve/reject recommendations.

RISK CONFIGURATION:
{json.dumps(self.risk_config, indent=2)}

CURRENT PORTFOLIO:
Account Value: ${account_value:,.2f}
Cash Balance: ${portfolio_data.get('cash_balance', 0):,.2f} ({cash_pct:.1f}%)
Positions: {len(positions)}

Position Concentrations:
{json.dumps(position_concentrations, indent=2)}

MARKET CONDITIONS:
VIX: {market_data.get('vix_level', 'N/A')}
Market Sentiment: {market_data.get('sentiment_signal', 'N/A')}
Market Data: {json.dumps(market_data.get('indices', {}), indent=2)}

PROPOSED RECOMMENDATIONS:
{json.dumps(all_recommendations, indent=2)}

Your Task:
1. Identify any CURRENT risk violations
2. Approve recommendations that are safe and prudent
3. REJECT recommendations that violate risk limits
4. Add FORCED actions if mandatory risk reduction needed
5. Provide overall risk assessment

Be conservative. When in doubt, protect capital."""

        try:
            # Call LLM using base class method
            response = self._call_llm(
                system_prompt=self.get_system_prompt(),
                user_prompt=user_prompt,
                json_mode=True
            )

            # Parse JSON response using base class method
            # If parsing fails, REJECT ALL recommendations (safe default)
            fallback = {
                'risk_level': 'CRITICAL',
                'portfolio_health': 50,
                'current_violations': ['Risk Manager parsing failed - rejecting all actions'],
                'approved_recommendations': [],
                'rejected_recommendations': all_recommendations,
                'forced_actions': [],
                'risk_alert': 'CRITICAL: Risk Manager JSON parsing failed. All recommendations rejected as safety measure.',
                'recommendations': 'Check Risk Manager output format.',
                'agent': 'RiskManager',
                'fallback': True
            }

            analysis = self._parse_json_response(response, default=fallback)

            # Add metadata
            analysis['agent'] = 'RiskManager'
            analysis['model_used'] = self.model
            analysis['risk_config'] = self.risk_config

            self._log_info(f"✓ Risk assessment complete")
            self._log_info(f"Risk Level: {analysis.get('risk_level', 'UNKNOWN')}")
            self._log_info(f"Approved: {len(analysis.get('approved_recommendations', []))}")
            self._log_info(f"Rejected: {len(analysis.get('rejected_recommendations', []))}")
            self._log_info(f"Forced Actions: {len(analysis.get('forced_actions', []))}")

            if analysis.get('current_violations'):
                self._log_warning(f"VIOLATIONS: {len(analysis['current_violations'])}")

            return analysis

        except Exception as e:
            self._log_error(f"Risk analysis failed: {e}")
            # If risk manager fails, REJECT ALL recommendations (safe default)
            return {
                'risk_level': 'CRITICAL',
                'portfolio_health': 50,
                'current_violations': ['Risk Manager failure - rejecting all actions'],
                'approved_recommendations': [],
                'rejected_recommendations': all_recommendations,
                'forced_actions': [],
                'risk_alert': f'CRITICAL: Risk Manager failed ({str(e)}). All recommendations rejected as safety measure.',
                'recommendations': 'Fix Risk Manager before proceeding.',
                'agent': 'RiskManager',
                'error': str(e)
            }


if __name__ == "__main__":
    # Test Risk Manager
    from config.llm_router_unified import UnifiedLLMRouter
    from config.settings import API_CONFIG
    from data.mock_data import MockDataGenerator

    print("\n" + "="*60)
    print("  RISK MANAGER AGENT - TEST")
    print("="*60 + "\n")

    # Initialize
    llm_router = UnifiedLLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )

    risk_manager = RiskManager(llm_router)
    mock_data = MockDataGenerator()

    # Get test data
    portfolio = mock_data.get_portfolio_data()
    market = mock_data.get_market_overview()

    # Sample recommendations
    recommendations = [
        {
            'ticker': 'MSFT',
            'action': 'REDUCE',
            'priority': 'HIGH',
            'confidence': 90,
            'reasoning': 'Concentration risk at 47%'
        },
        {
            'ticker': 'TSLA',
            'action': 'SELL',
            'priority': 'HIGH',
            'confidence': 85,
            'reasoning': 'Losing position in bearish market'
        },
        {
            'ticker': 'NVDA',
            'action': 'BUY',
            'priority': 'MEDIUM',
            'confidence': 70,
            'reasoning': 'Strong technical setup'
        }
    ]

    # Run risk analysis
    result = risk_manager.analyze(portfolio, market, recommendations)

    # Display results
    print("\n🛡️  RISK ASSESSMENT:")
    print(f"\nRisk Level: {result.get('risk_level', 'N/A')}")
    print(f"Portfolio Health: {result.get('portfolio_health', 'N/A')}/100")

    if result.get('current_violations'):
        print(f"\n⚠️  ACTIVE VIOLATIONS ({len(result['current_violations'])}):")
        for violation in result['current_violations']:
            print(f"  ! {violation}")

    print(f"\n✅ APPROVED RECOMMENDATIONS ({len(result.get('approved_recommendations', []))}):")
    for rec in result.get('approved_recommendations', []):
        print(f"  ✓ {rec['ticker']}: {rec['action']} - {rec['reasoning']}")

    if result.get('rejected_recommendations'):
        print(f"\n❌ REJECTED RECOMMENDATIONS ({len(result['rejected_recommendations'])}):")
        for rec in result['rejected_recommendations']:
            print(f"  ✗ {rec['ticker']}: {rec['action']} - {rec.get('rejection_reason', 'N/A')}")

    if result.get('forced_actions'):
        print(f"\n🚨 FORCED ACTIONS ({len(result['forced_actions'])}):")
        for action in result['forced_actions']:
            print(f"  ! {action['ticker']}: {action['action']} - {action['reasoning']}")

    print(f"\nRisk Alert: {result.get('risk_alert', 'N/A')}")
    print(f"\n💰 Cost: ${llm_router.get_total_cost():.4f}\n")
