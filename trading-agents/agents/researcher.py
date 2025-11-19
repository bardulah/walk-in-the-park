"""
Researcher Agent
Provides bull/bear debate mechanism for adversarial analysis
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent


# System prompts for bull and bear researchers
BULL_RESEARCHER_SYSTEM_PROMPT = """You are a BULLISH RESEARCHER with expertise in finding growth opportunities and optimistic scenarios.

Your role in the trading firm is to:
1. Identify optimistic scenarios and growth catalysts in analyst reports
2. Challenge overly bearish or pessimistic assumptions
3. Present contrarian bull cases that others might miss
4. Find hidden value and underappreciated strengths
5. Argue for why risks may be overblown or manageable

Guidelines:
- Be critical but constructive - use data and logic to support arguments
- Don't be blindly optimistic - acknowledge real risks but argue why they're manageable
- Look for asymmetric upside opportunities
- Consider multiple timeframes (short-term catalysts, long-term growth)
- Reference specific data points from analyst reports to support your case
- Quantify potential upside when possible

Output Format (JSON):
{
    "bull_case_summary": "2-3 sentence summary of the optimistic scenario",
    "growth_catalysts": ["catalyst 1", "catalyst 2", ...],
    "underappreciated_strengths": ["strength 1", "strength 2", ...],
    "risk_rebuttals": [
        {"risk": "identified risk", "rebuttal": "why it's manageable or overblown"}
    ],
    "upside_potential": "quantified potential upside (%, $, or qualitative)",
    "conviction_level": "high|medium|low",
    "key_assumptions": ["assumption 1", "assumption 2", ...],
    "recommendation": "strong_buy|buy|hold",
    "reasoning": "detailed reasoning for recommendation"
}
"""

BEAR_RESEARCHER_SYSTEM_PROMPT = """You are a BEARISH RESEARCHER with expertise in risk identification and downside scenario analysis.

Your role in the trading firm is to:
1. Identify risks and red flags that analysts may have overlooked
2. Challenge overly bullish or optimistic assumptions
3. Present contrarian bear cases and worst-case scenarios
4. Find hidden risks and overvalued aspects
5. Argue for why positive factors may be temporary or overstated

Guidelines:
- Be critical but constructive - use data and logic to support arguments
- Don't be blindly pessimistic - acknowledge real strengths but argue why they may not matter
- Look for asymmetric downside risks
- Consider multiple timeframes (short-term headwinds, long-term structural issues)
- Reference specific data points from analyst reports to support your case
- Quantify potential downside when possible

Output Format (JSON):
{
    "bear_case_summary": "2-3 sentence summary of the pessimistic scenario",
    "risk_factors": ["risk 1", "risk 2", ...],
    "overvalued_aspects": ["aspect 1", "aspect 2", ...],
    "strength_rebuttals": [
        {"strength": "identified strength", "rebuttal": "why it's temporary or overstated"}
    ],
    "downside_potential": "quantified potential downside (%, $, or qualitative)",
    "conviction_level": "high|medium|low",
    "key_assumptions": ["assumption 1", "assumption 2", ...],
    "recommendation": "strong_sell|sell|hold",
    "reasoning": "detailed reasoning for recommendation"
}
"""


class ResearcherAgent(BaseAgent):
    """
    Researcher agent that provides adversarial analysis through bull/bear debate

    This agent reviews analyst reports and provides contrarian perspectives,
    either arguing for optimistic scenarios (bull) or identifying risks (bear).

    Inspired by TradingAgents framework research showing that debate-driven
    decision making improves trading performance by 15-25%.
    """

    def __init__(self, llm_router, stance: str, model: str = "gpt-4o-mini"):
        """
        Initialize researcher agent

        Args:
            llm_router: LLM router for model calls
            stance: Research stance - either 'bull' or 'bear'
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        if stance not in ['bull', 'bear']:
            raise ValueError(f"Invalid stance '{stance}'. Must be 'bull' or 'bear'")

        self.stance = stance

        super().__init__(
            llm_router=llm_router,
            model=model,
            temperature=0.7,  # Higher temperature for diverse perspectives
            max_tokens=1500,
            agent_name=f"{stance.title()} Researcher"
        )

    def get_system_prompt(self) -> str:
        """Get system prompt based on stance"""
        if self.stance == 'bull':
            return BULL_RESEARCHER_SYSTEM_PROMPT
        else:
            return BEAR_RESEARCHER_SYSTEM_PROMPT

    def analyze(self, analyst_reports: Dict[str, Any], ticker: str = None) -> Dict[str, Any]:
        """
        Analyze analyst reports from contrarian perspective

        Args:
            analyst_reports: Dict containing reports from various analysts
                Expected keys: 'portfolio', 'market', 'technical', 'news', etc.
            ticker: Optional ticker symbol for context

        Returns:
            Dict containing contrarian analysis from bull/bear perspective
        """
        self._log_progress(
            f"analyzing from {self.stance} perspective...",
            emoji="🐂" if self.stance == 'bull' else "🐻"
        )

        # Build user prompt with analyst reports
        user_prompt = self._build_debate_prompt(analyst_reports, ticker)

        try:
            # Call LLM
            response = self._call_llm(
                system_prompt=self.get_system_prompt(),
                user_prompt=user_prompt,
                json_mode=True
            )

            # Parse response
            result = self._parse_json_response(response)

            # Add metadata
            result['stance'] = self.stance
            result['agent'] = self.agent_name
            result['success'] = True

            self._log_info(
                f"{self.stance.title()} case: {result.get('conviction_level', 'unknown')} conviction"
            )

            return result

        except Exception as e:
            self._log_error(f"Analysis failed: {str(e)}", exc_info=True)
            return self._build_error_response(e)

    def _build_debate_prompt(self, analyst_reports: Dict[str, Any], ticker: str = None) -> str:
        """
        Build debate prompt from analyst reports

        Args:
            analyst_reports: Dict of analyst reports
            ticker: Optional ticker symbol

        Returns:
            Formatted prompt string
        """
        ticker_context = f"for {ticker}" if ticker else ""

        prompt_parts = [
            f"Review the following analyst reports {ticker_context} and provide your {self.stance} perspective.\n",
            "# Analyst Reports\n"
        ]

        # Add each analyst report
        for agent_name, report in analyst_reports.items():
            if isinstance(report, dict) and report.get('success', True):
                prompt_parts.append(f"\n## {agent_name.replace('_', ' ').title()}\n")

                # Extract key information from report
                if 'recommendation' in report:
                    prompt_parts.append(f"Recommendation: {report['recommendation']}\n")

                if 'analysis' in report:
                    prompt_parts.append(f"Analysis: {report['analysis']}\n")

                if 'summary' in report:
                    prompt_parts.append(f"Summary: {report['summary']}\n")

                if 'key_findings' in report:
                    prompt_parts.append(f"Key Findings: {report['key_findings']}\n")

                # Include risk/opportunity assessment if present
                if 'risks' in report:
                    prompt_parts.append(f"Risks: {report['risks']}\n")

                if 'opportunities' in report:
                    prompt_parts.append(f"Opportunities: {report['opportunities']}\n")

        prompt_parts.append(
            f"\n# Your Task\n\n"
            f"As a {self.stance} researcher, critically analyze these reports. "
            f"{'Identify growth catalysts and argue why concerns may be overblown.' if self.stance == 'bull' else 'Identify risks and argue why optimistic assumptions may be wrong.'}\n\n"
            f"Provide your {self.stance} perspective in the specified JSON format."
        )

        return "".join(prompt_parts)

    def debate(self, other_researcher_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Respond to opposing researcher's analysis

        Args:
            other_researcher_analysis: Analysis from the opposing researcher

        Returns:
            Dict containing rebuttal/response
        """
        if not isinstance(other_researcher_analysis, dict):
            raise ValueError("other_researcher_analysis must be a dict")

        opposing_stance = other_researcher_analysis.get('stance', 'unknown')

        self._log_progress(
            f"debating with {opposing_stance} researcher...",
            emoji="💬"
        )

        # Build rebuttal prompt
        prompt = f"""Review the opposing {opposing_stance} researcher's analysis and provide a rebuttal.

# {opposing_stance.title()} Researcher's Analysis
{self._format_analysis_for_debate(other_researcher_analysis)}

# Your Task
As a {self.stance} researcher, provide a point-by-point rebuttal to the opposing analysis.
Focus on:
1. Which points do you agree with (be fair and objective)
2. Which points do you disagree with and why
3. What key factors they may have missed
4. Your refined {self.stance} case after considering their arguments

Provide response in JSON format:
{{
    "agreements": ["point 1", "point 2"],
    "disagreements": [
        {{"point": "their argument", "rebuttal": "your counter-argument"}}
    ],
    "missed_factors": ["factor 1", "factor 2"],
    "refined_case": "your updated {self.stance} case after debate",
    "confidence_change": "increased|decreased|unchanged",
    "final_conviction": "high|medium|low"
}}
"""

        try:
            response = self._call_llm(
                system_prompt=self.get_system_prompt(),
                user_prompt=prompt,
                json_mode=True
            )

            result = self._parse_json_response(response)
            result['stance'] = self.stance
            result['debated_with'] = opposing_stance
            result['success'] = True

            return result

        except Exception as e:
            self._log_error(f"Debate failed: {str(e)}", exc_info=True)
            return self._build_error_response(e)

    def _format_analysis_for_debate(self, analysis: Dict[str, Any]) -> str:
        """Format analysis for debate prompt"""
        key_fields = [
            'bull_case_summary', 'bear_case_summary',
            'growth_catalysts', 'risk_factors',
            'recommendation', 'reasoning',
            'conviction_level'
        ]

        parts = []
        for field in key_fields:
            if field in analysis:
                field_name = field.replace('_', ' ').title()
                parts.append(f"{field_name}: {analysis[field]}")

        return "\n".join(parts)

    def synthesize_debate(
        self,
        bull_analysis: Dict[str, Any],
        bear_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesize bull and bear analyses into balanced perspective

        This is useful for getting a neutral view after the debate.

        Args:
            bull_analysis: Bull researcher's analysis
            bear_analysis: Bear researcher's analysis

        Returns:
            Synthesized balanced analysis
        """
        self._log_progress("synthesizing debate results...", emoji="⚖️")

        prompt = f"""You are reviewing a debate between bull and bear researchers.
Provide a balanced synthesis that considers both perspectives.

# Bull Researcher's Analysis
{self._format_analysis_for_debate(bull_analysis)}

# Bear Researcher's Analysis
{self._format_analysis_for_debate(bear_analysis)}

# Your Task
Synthesize these opposing viewpoints into a balanced perspective.

Provide response in JSON format:
{{
    "balanced_summary": "2-3 sentence balanced summary",
    "strongest_bull_arguments": ["argument 1", "argument 2"],
    "strongest_bear_arguments": ["argument 1", "argument 2"],
    "key_uncertainties": ["uncertainty 1", "uncertainty 2"],
    "risk_reward_assessment": "description of risk/reward balance",
    "recommended_action": "buy|sell|hold|wait_for_clarity",
    "confidence": "high|medium|low",
    "reasoning": "detailed reasoning for recommendation",
    "conditions_to_monitor": ["condition 1", "condition 2"]
}}
"""

        try:
            # Use lower temperature for synthesis (more balanced)
            response = self._call_llm(
                system_prompt="You are an objective financial analyst synthesizing debate results.",
                user_prompt=prompt,
                temperature=0.5,  # Lower than debate temperature
                json_mode=True
            )

            result = self._parse_json_response(response)
            result['synthesis'] = True
            result['success'] = True

            self._log_info(
                f"Synthesis complete: {result.get('recommended_action', 'unknown')}"
            )

            return result

        except Exception as e:
            self._log_error(f"Synthesis failed: {str(e)}", exc_info=True)
            return self._build_error_response(e)
