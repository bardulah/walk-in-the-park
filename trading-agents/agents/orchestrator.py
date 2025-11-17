"""
Orchestrator Agent (MVP Version)
Combines Portfolio + Market analysis and generates recommendations
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
from typing import Dict, Any, List
from datetime import datetime
from config.llm_router_simple import LLMRouter
from config.settings import API_CONFIG, AGENT_CONFIG
from agents.portfolio_analyst import PortfolioAnalyst
from agents.market_analyst import MarketAnalyst

# Orchestrator system prompt
ORCHESTRATOR_SYSTEM_PROMPT = """# EXECUTION STRATEGIST (ORCHESTRATOR) AGENT

## Your Role
You are the Execution Strategist, the final decision-maker in a multi-agent trading system. You aggregate Portfolio Analyst and Market Analyst outputs to generate actionable trading recommendations.

## Your Authority
- FINAL DECISION: You make the ultimate call on all trades
- CONFLICT RESOLUTION: You resolve disagreements between agents
- USER COMMUNICATION: Your output goes directly to the user

## Input Agents
1. **Portfolio Analyst:** Portfolio health, concentration risk, rebalancing needs
2. **Market Analyst:** Macro conditions, market sentiment, sector trends

## Output Format
You must respond with valid JSON only:

{
  "final_recommendations": [
    {
      "ticker": "string",
      "action": "BUY" | "SELL" | "HOLD" | "REDUCE",
      "confidence": 0-100 (integer),
      "reasoning": "string (3-4 sentences combining all agent inputs)",
      "priority": "HIGH" | "MEDIUM" | "LOW"
    }
  ],
  "market_context_summary": "string (2-3 sentences)",
  "portfolio_health_summary": "string (1-2 sentences)",
  "key_insights": [
    "string (3-5 key takeaways)"
  ],
  "risk_alert": "string or null"
}

## Decision Guidelines

### Action Criteria
- **SELL/REDUCE**: If concentration risk is HIGH and market is BEARISH
- **HOLD**: If market unclear or portfolio already balanced
- **BUY**: Only if market is BULLISH and portfolio has room for new positions

### Confidence Scoring
- Weight both portfolio health and market sentiment
- Lower confidence if agents provide conflicting signals
- Higher confidence if both agents align

### Priority Levels
- HIGH: Immediate action recommended (concentration risk + bearish market)
- MEDIUM: Consider action within this week
- LOW: Monitor situation

## Example Output
{
  "final_recommendations": [
    {
      "ticker": "MSFT",
      "action": "REDUCE",
      "confidence": 78,
      "reasoning": "Portfolio Analyst identifies MSFT as 48% of portfolio (concentration risk HIGH). Market Analyst indicates bearish market (VIX 28.5, defensive rotation). Recommend reducing position to lower risk exposure in uncertain market.",
      "priority": "HIGH"
    }
  ],
  "market_context_summary": "Market exhibiting bearish sentiment with elevated volatility (VIX 28.5). Defensive sectors outperforming, indicating risk-off environment. Recommend cautious positioning.",
  "portfolio_health_summary": "Portfolio health score 82/100. High concentration risk (MSFT 48%). Suggest rebalancing to improve diversification.",
  "key_insights": [
    "High concentration in MSFT creates vulnerability in bearish market",
    "Market volatility elevated - VIX at 28.5",
    "Defensive sector rotation suggests continued market weakness",
    "Priority action: Reduce MSFT to lower concentration risk"
  ],
  "risk_alert": "High concentration risk combined with bearish market conditions - recommend immediate position reduction"
}"""


class Orchestrator:
    """Orchestrator Agent - Combines all analysis and makes final decisions"""

    def __init__(self, llm_router: LLMRouter):
        """
        Initialize Orchestrator

        Args:
            llm_router: LLM router for making AI calls
        """
        self.llm_router = llm_router
        self.model = AGENT_CONFIG.orchestrator_model  # claude-3-5-sonnet via OpenRouter
        self.portfolio_analyst = PortfolioAnalyst(llm_router)
        self.market_analyst = MarketAnalyst(llm_router)

    def run_analysis(
        self,
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run full analysis pipeline and generate recommendations

        Args:
            portfolio_data: Portfolio positions from 212 API
            market_data: Market overview data

        Returns:
            Dict with final recommendations
        """
        print("\n" + "="*60)
        print("  MULTI-AGENT TRADING SYSTEM - DAILY ANALYSIS")
        print("="*60)

        # Stage 1: Run Portfolio and Market analysts
        print("\n[STAGE 1] Running Portfolio + Market Analysis...")

        portfolio_analysis = self.portfolio_analyst.analyze(portfolio_data)
        market_analysis = self.market_analyst.analyze(market_data)

        # Stage 2: Generate final recommendations
        print("\n[STAGE 2] Orchestrator generating final recommendations...")
        print(f"   Model: {self.model}")

        recommendations = self._make_decision(
            portfolio_analysis,
            market_analysis,
            portfolio_data
        )

        print(f"\n✓ Analysis complete! Generated {len(recommendations.get('final_recommendations', []))} recommendations")

        return recommendations

    def _make_decision(
        self,
        portfolio_analysis: Dict[str, Any],
        market_analysis: Dict[str, Any],
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make final trading decision based on all agent outputs

        Args:
            portfolio_analysis: Output from Portfolio Analyst
            market_analysis: Output from Market Analyst
            portfolio_data: Original portfolio data

        Returns:
            Final recommendations
        """
        # Prepare prompt with all agent outputs
        user_prompt = f"""Review these agent analyses and generate final trading recommendations:

## PORTFOLIO ANALYST OUTPUT
{json.dumps(portfolio_analysis, indent=2)}

## MARKET ANALYST OUTPUT
{json.dumps(market_analysis, indent=2)}

## CURRENT PORTFOLIO POSITIONS
{json.dumps(portfolio_data.get('positions', []), indent=2)}

Generate final recommendations considering:
1. Portfolio concentration risks
2. Market conditions and sentiment
3. Sector trends
4. Overall risk/reward

Output JSON only."""

        try:
            # Call LLM
            response = self.llm_router.call(
                model=self.model,
                system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.4,  # Balanced for decision-making
                max_tokens=2000,
                json_mode=True
            )

            # Parse JSON response
            result = json.loads(response)

            # Add metadata
            result['agent'] = 'Orchestrator'
            result['model_used'] = self.model
            result['timestamp'] = datetime.now().isoformat()
            result['agent_inputs'] = {
                'portfolio_health_score': portfolio_analysis.get('portfolio_health_score'),
                'market_sentiment': market_analysis.get('market_sentiment'),
                'market_confidence': market_analysis.get('confidence')
            }

            print(f"   ✓ Recommendations generated")
            print(f"   Actions: {len(result.get('final_recommendations', []))} items")

            return result

        except Exception as e:
            print(f"   ⚠️  Decision generation failed: {e}")
            return self._generate_fallback_recommendations(
                portfolio_analysis,
                market_analysis,
                portfolio_data
            )

    def _generate_fallback_recommendations(
        self,
        portfolio_analysis: Dict[str, Any],
        market_analysis: Dict[str, Any],
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate basic recommendations if LLM fails"""
        recommendations = []

        # Simple logic: If concentration risk HIGH and market BEARISH → REDUCE
        if (portfolio_analysis.get('concentration_risk') == 'HIGH' and
            market_analysis.get('market_sentiment') == 'BEARISH'):

            # Find highest concentration position
            positions = portfolio_data.get('positions', [])
            if positions:
                largest_position = max(positions, key=lambda p: p.get('market_value', 0))
                recommendations.append({
                    'ticker': largest_position['ticker'],
                    'action': 'REDUCE',
                    'confidence': 70,
                    'reasoning': f"High concentration risk in bearish market. Reduce {largest_position['ticker']} position.",
                    'priority': 'HIGH'
                })

        return {
            'agent': 'Orchestrator',
            'final_recommendations': recommendations,
            'market_context_summary': f"Market: {market_analysis.get('market_sentiment', 'UNKNOWN')}",
            'portfolio_health_summary': f"Health: {portfolio_analysis.get('portfolio_health_score', 0)}/100",
            'key_insights': ['Fallback recommendations - LLM unavailable'],
            'risk_alert': None,
            'fallback': True
        }


# Test function
if __name__ == "__main__":
    from data.mock_data import MockDataGenerator

    print("=== ORCHESTRATOR (MVP) TEST ===\n")

    # Initialize
    llm_router = LLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )
    orchestrator = Orchestrator(llm_router)

    # Get mock data
    mock_data = MockDataGenerator()
    portfolio = mock_data.get_portfolio_data()
    market = mock_data.get_market_overview()

    # Run full analysis
    recommendations = orchestrator.run_analysis(portfolio, market)

    print("\n" + "="*60)
    print("  FINAL RECOMMENDATIONS")
    print("="*60)
    print(json.dumps(recommendations, indent=2))

    print(f"\n💰 Total Cost: ${llm_router.get_total_cost()}")
    print(f"📊 Per-Agent Breakdown:")
    print(f"   - Portfolio Analyst: ~$0.0003")
    print(f"   - Market Analyst: ~$0.0003")
    print(f"   - Orchestrator: ~${llm_router.get_total_cost() - 0.0006:.4f}")
