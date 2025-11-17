"""
Portfolio Analyst Agent
Analyzes portfolio health and identifies concentration risks
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
from typing import Dict, Any
from config.llm_router_simple import LLMRouter
from config.settings import API_CONFIG, AGENT_CONFIG

# System prompt from AGENT_SPECIFICATIONS.md
PORTFOLIO_ANALYST_SYSTEM_PROMPT = """# PORTFOLIO ANALYST AGENT

## Your Role
You are a Portfolio Analyst for a daily stock market monitoring system. Your sole responsibility is to analyze the user's current portfolio and identify risks, imbalances, and opportunities.

## Your Capabilities
- Calculate portfolio health metrics
- Identify concentration risks
- Detect sector imbalances
- Suggest rebalancing opportunities
- Provide factual analysis (no buy/sell recommendations)

## Your Constraints
- You DO NOT make buy/sell recommendations (other agents handle that)
- You DO NOT predict market movements
- You focus on portfolio construction and risk distribution
- You provide objective, factual analysis only

## Output Format
You must respond with valid JSON only (no markdown, no explanations):

{
  "portfolio_health_score": 0-100 (integer),
  "total_positions": integer,
  "top_holding_pct": float (percentage of portfolio in largest position),
  "concentration_risk": "LOW" | "MEDIUM" | "HIGH",
  "sector_distribution": {
    "Technology": float,
    "Healthcare": float
  },
  "sector_risk_assessment": "BALANCED" | "CONCENTRATED" | "VERY_CONCENTRATED",
  "rebalance_opportunities": [
    {
      "action": "REDUCE" | "INCREASE",
      "ticker": "string",
      "reason": "string (1 sentence)",
      "current_pct": float,
      "target_pct": float
    }
  ],
  "key_findings": [
    "string (max 3 bullet points)"
  ]
}

## Scoring Guidelines

### Portfolio Health Score (0-100)
- 90-100: Excellent diversification, low concentration, balanced sectors
- 70-89: Good diversification, minor concentration issues
- 50-69: Moderate issues, some concentration or sector imbalance
- 30-49: Significant risks, high concentration or poor diversification
- 0-29: Critical issues, immediate rebalancing recommended

### Concentration Risk
- LOW: Largest holding < 20% of portfolio
- MEDIUM: Largest holding 20-35% of portfolio
- HIGH: Largest holding > 35% of portfolio

### Sector Risk
- BALANCED: No sector > 40% of portfolio
- CONCENTRATED: One sector 40-60% of portfolio
- VERY_CONCENTRATED: One sector > 60% of portfolio

## Analysis Steps
1. Calculate total portfolio value
2. Determine percentage of each position
3. Identify largest holding and concentration level
4. Categorize stocks by sector
5. Calculate sector distribution
6. Assess overall portfolio health
7. Identify specific rebalancing opportunities
8. Generate concise key findings"""


class PortfolioAnalyst:
    """Portfolio Analyst Agent"""

    def __init__(self, llm_router: LLMRouter):
        """
        Initialize Portfolio Analyst

        Args:
            llm_router: LLM router for making AI calls
        """
        self.llm_router = llm_router
        self.model = AGENT_CONFIG.portfolio_model  # gpt-4o-mini via OpenRouter

    def analyze(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze portfolio and generate health assessment

        Args:
            portfolio_data: Portfolio data with positions

        Returns:
            Dict with portfolio health analysis
        """
        print(f"\n🔍 Portfolio Analyst analyzing portfolio...")
        print(f"   Model: {self.model}")

        # Generate user prompt
        user_prompt = f"""Analyze this portfolio and provide health assessment:

{json.dumps(portfolio_data, indent=2)}

Calculate:
1. Portfolio health score (0-100)
2. Concentration risk level
3. Sector distribution
4. Specific rebalancing recommendations

Output JSON only (no additional text)."""

        try:
            # Call LLM
            response = self.llm_router.call(
                model=self.model,
                system_prompt=PORTFOLIO_ANALYST_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,  # Low temperature for factual analysis
                max_tokens=1000,
                json_mode=True
            )

            # Parse JSON response
            result = json.loads(response)

            # Add metadata
            result['agent'] = 'PortfolioAnalyst'
            result['model_used'] = self.model
            result['timestamp'] = portfolio_data.get('timestamp')

            print(f"   ✓ Analysis complete")
            print(f"   Health Score: {result.get('portfolio_health_score', 0)}/100")
            print(f"   Concentration Risk: {result.get('concentration_risk', 'UNKNOWN')}")

            return result

        except json.JSONDecodeError as e:
            print(f"   ⚠️  Failed to parse JSON response: {e}")
            print(f"   Raw response: {response[:200]}...")
            # Return fallback
            return self._generate_fallback_analysis(portfolio_data)

        except Exception as e:
            print(f"   ⚠️  Analysis failed: {e}")
            return self._generate_fallback_analysis(portfolio_data)

    def _generate_fallback_analysis(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic fallback analysis if LLM fails"""
        positions = portfolio_data.get('positions', [])
        total_value = portfolio_data.get('total_value', 0)

        if not positions or total_value == 0:
            return {
                'agent': 'PortfolioAnalyst',
                'error': 'No portfolio data available',
                'portfolio_health_score': 0,
                'total_positions': 0,
                'key_findings': ['No positions in portfolio']
            }

        # Simple calculations
        largest_position_value = max((p.get('market_value', 0) for p in positions), default=0)
        largest_pct = (largest_position_value / total_value * 100) if total_value > 0 else 0

        concentration_risk = "LOW"
        if largest_pct > 35:
            concentration_risk = "HIGH"
        elif largest_pct > 20:
            concentration_risk = "MEDIUM"

        return {
            'agent': 'PortfolioAnalyst',
            'portfolio_health_score': 50,  # Default medium score
            'total_positions': len(positions),
            'top_holding_pct': round(largest_pct, 2),
            'concentration_risk': concentration_risk,
            'sector_distribution': {},
            'sector_risk_assessment': 'UNKNOWN',
            'rebalance_opportunities': [],
            'key_findings': [
                f"Portfolio has {len(positions)} positions",
                f"Largest position: {round(largest_pct, 1)}% of portfolio",
                "Fallback analysis - LLM unavailable"
            ],
            'fallback': True
        }


# Test function
if __name__ == "__main__":
    from data.mock_data import MockDataGenerator

    print("=== PORTFOLIO ANALYST TEST ===\n")

    # Initialize
    llm_router = LLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )
    analyst = PortfolioAnalyst(llm_router)

    # Get mock portfolio data
    mock_data = MockDataGenerator()
    portfolio = mock_data.get_portfolio_data()

    print("Input Portfolio:")
    print(json.dumps(portfolio, indent=2))

    # Analyze
    result = analyst.analyze(portfolio)

    print("\n" + "="*50)
    print("Portfolio Analysis Result:")
    print("="*50)
    print(json.dumps(result, indent=2))

    print(f"\n💰 Cost: ${llm_router.get_total_cost()}")
