"""
Market Analyst Agent
Analyzes macro market conditions and provides sentiment assessment
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
from typing import Dict, Any
from config.llm_router_simple import LLMRouter
from config.settings import API_CONFIG, AGENT_CONFIG
from utils.json_parser import safe_json_parse
from agents.base_agent import BaseAgent

# System prompt from AGENT_SPECIFICATIONS.md (truncated for brevity)
MARKET_ANALYST_SYSTEM_PROMPT = """# MARKET ANALYST AGENT

## Your Role
You are a Market Analyst specializing in macro market analysis and sector rotation. You analyze broad market conditions to provide context for stock-specific trading decisions.

## Your Capabilities
- Analyze market indices and volatility
- Assess market sentiment (bullish/neutral/bearish)
- Identify sector rotation patterns
- Detect macro risk factors
- Provide confidence-scored market outlook

## Output Format
You must respond with valid JSON only:

{
  "market_sentiment": "BULLISH" | "NEUTRAL" | "BEARISH",
  "confidence": 0-100 (integer),
  "market_regime": "RISK_ON" | "RISK_OFF" | "TRANSITIONAL",
  "volatility_assessment": "LOW" | "MODERATE" | "HIGH" | "EXTREME",
  "key_drivers": [
    "string (3-5 bullet points)"
  ],
  "sector_trends": {
    "outperforming": ["sector1", "sector2"],
    "underperforming": ["sector3", "sector4"],
    "rotation_signal": "DEFENSIVE" | "CYCLICAL" | "GROWTH" | "NEUTRAL"
  },
  "risk_factors": [
    {
      "factor": "string",
      "severity": "LOW" | "MEDIUM" | "HIGH",
      "impact": "string (1 sentence)"
    }
  ],
  "recommendation_context": "string (2-3 sentences)",
  "reasoning": "string (3-4 sentences)"
}

## Analysis Framework

### Market Sentiment Criteria
**BULLISH:** S&P up, VIX < 20, risk-on sectors outperforming
**NEUTRAL:** Mixed signals, VIX 20-30, choppy action
**BEARISH:** S&P down, VIX > 30, defensive sectors outperforming

### Volatility Assessment
- LOW: VIX < 15
- MODERATE: VIX 15-25
- HIGH: VIX 25-35
- EXTREME: VIX > 35

### Confidence Scoring
- 90-100: Very high conviction
- 70-89: High conviction
- 50-69: Moderate conviction
- 30-49: Low conviction"""


class MarketAnalyst(BaseAgent):
    """Market Analyst Agent"""

    def __init__(self, llm_router: LLMRouter):
        """
        Initialize Market Analyst

        Args:
            llm_router: LLM router for making AI calls
        """
        super().__init__(
            llm_router=llm_router,
            model=AGENT_CONFIG.market_model,
            temperature=0.5,  # Moderate temperature for analysis
            max_tokens=1500,
            agent_name="Market Analyst"
        )

    def get_system_prompt(self) -> str:
        """Get system prompt for Market Analyst"""
        return MARKET_ANALYST_SYSTEM_PROMPT

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market conditions and generate sentiment assessment

        Args:
            market_data: Market data with indices

        Returns:
            Dict with market analysis
        """
        self._log_progress("analyzing market conditions...", emoji="📊")

        # Generate user prompt
        user_prompt = f"""Analyze current market conditions:

{json.dumps(market_data, indent=2)}

Provide:
1. Market sentiment (BULLISH/NEUTRAL/BEARISH) with confidence score
2. Volatility assessment based on VIX
3. Sector rotation analysis
4. Key risk factors
5. Recommendation context for stock selection

Output JSON only (no additional text)."""

        try:
            # Call LLM using base class method
            response = self._call_llm(
                system_prompt=self.get_system_prompt(),
                user_prompt=user_prompt,
                json_mode=True
            )

            # Parse JSON response using base class method
            result = self._parse_json_response(
                response,
                default=self._generate_fallback_analysis(market_data)
            )

            # Add metadata
            result['agent'] = 'MarketAnalyst'
            result['model_used'] = self.model
            result['timestamp'] = market_data.get('timestamp')

            self._log_info(f"✓ Analysis complete")
            self._log_info(f"Sentiment: {result.get('market_sentiment', 'UNKNOWN')} ({result.get('confidence', 0)}% confidence)")
            self._log_info(f"Volatility: {result.get('volatility_assessment', 'UNKNOWN')}")

            return result

        except Exception as e:
            self._log_error(f"Analysis failed: {e}")
            return self._generate_fallback_analysis(market_data)

    def _generate_fallback_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic fallback analysis if LLM fails"""
        # Extract VIX and sentiment signal from data
        vix = market_data.get('vix_level', 20)
        sentiment_signal = market_data.get('sentiment_signal', 'NEUTRAL')

        # Simple volatility assessment based on VIX
        if vix < 15:
            volatility = "LOW"
        elif vix < 25:
            volatility = "MODERATE"
        elif vix < 35:
            volatility = "HIGH"
        else:
            volatility = "EXTREME"

        # Map sentiment signal to market regime
        if sentiment_signal == 'BULLISH':
            regime = "RISK_ON"
        elif sentiment_signal == 'BEARISH':
            regime = "RISK_OFF"
        else:
            regime = "TRANSITIONAL"

        return {
            'agent': 'MarketAnalyst',
            'market_sentiment': sentiment_signal,
            'confidence': 50,  # Default medium confidence
            'market_regime': regime,
            'volatility_assessment': volatility,
            'key_drivers': [
                f"VIX at {vix} indicates {volatility.lower()} volatility",
                "Fallback analysis - LLM unavailable"
            ],
            'sector_trends': {
                'outperforming': [],
                'underperforming': [],
                'rotation_signal': 'NEUTRAL'
            },
            'risk_factors': [],
            'recommendation_context': "Using fallback analysis due to LLM unavailability.",
            'reasoning': "Basic market assessment based on VIX and index movements.",
            'fallback': True
        }


# Test function
if __name__ == "__main__":
    from data.mock_data import MockDataGenerator

    print("=== MARKET ANALYST TEST ===\n")

    # Initialize
    llm_router = LLMRouter(
        gemini_api_key=API_CONFIG.gemini_api_key,
        openrouter_api_key=API_CONFIG.openrouter_api_key
    )
    analyst = MarketAnalyst(llm_router)

    # Get mock market data
    mock_data = MockDataGenerator()
    market = mock_data.get_market_overview()

    print("Input Market Data:")
    print(json.dumps(market, indent=2))

    # Analyze
    result = analyst.analyze(market)

    print("\n" + "="*50)
    print("Market Analysis Result:")
    print("="*50)
    print(json.dumps(result, indent=2))

    print(f"\n💰 Cost: ${llm_router.get_total_cost()}")
