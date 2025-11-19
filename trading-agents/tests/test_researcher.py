"""Tests for ResearcherAgent"""
import pytest
from agents.researcher import ResearcherAgent


class TestResearcherAgent:
    """Test ResearcherAgent functionality"""

    def test_init_bull_researcher(self, mock_llm_router):
        """Test bull researcher initialization"""
        researcher = ResearcherAgent(mock_llm_router, stance='bull')

        assert researcher.stance == 'bull'
        assert researcher.agent_name == 'Bull Researcher'
        assert researcher.temperature == 0.7  # Higher for diverse perspectives

    def test_init_bear_researcher(self, mock_llm_router):
        """Test bear researcher initialization"""
        researcher = ResearcherAgent(mock_llm_router, stance='bear')

        assert researcher.stance == 'bear'
        assert researcher.agent_name == 'Bear Researcher'

    def test_invalid_stance_raises_error(self, mock_llm_router):
        """Test that invalid stance raises ValueError"""
        with pytest.raises(ValueError, match="Invalid stance"):
            ResearcherAgent(mock_llm_router, stance='neutral')

    def test_get_system_prompt_bull(self, mock_llm_router):
        """Test bull researcher system prompt"""
        researcher = ResearcherAgent(mock_llm_router, stance='bull')
        prompt = researcher.get_system_prompt()

        assert 'BULLISH RESEARCHER' in prompt
        assert 'growth catalysts' in prompt.lower()
        assert 'optimistic' in prompt.lower()

    def test_get_system_prompt_bear(self, mock_llm_router):
        """Test bear researcher system prompt"""
        researcher = ResearcherAgent(mock_llm_router, stance='bear')
        prompt = researcher.get_system_prompt()

        assert 'BEARISH RESEARCHER' in prompt
        assert 'risk' in prompt.lower()
        assert 'downside' in prompt.lower()

    def test_build_debate_prompt(self, mock_llm_router):
        """Test debate prompt building"""
        researcher = ResearcherAgent(mock_llm_router, stance='bull')

        analyst_reports = {
            'portfolio': {
                'recommendation': 'hold',
                'summary': 'Portfolio is balanced',
                'success': True
            },
            'market': {
                'recommendation': 'bullish',
                'summary': 'Strong market conditions',
                'success': True
            }
        }

        prompt = researcher._build_debate_prompt(analyst_reports, ticker='AAPL')

        assert 'AAPL' in prompt
        assert 'Portfolio' in prompt
        assert 'Market' in prompt
        assert 'hold' in prompt
        assert 'bullish' in prompt

    def test_analyze_bull_case(self, mock_llm_router):
        """Test bull case analysis"""
        researcher = ResearcherAgent(mock_llm_router, stance='bull')

        analyst_reports = {
            'market': {'recommendation': 'buy', 'success': True}
        }

        # Mock will return a basic JSON response
        result = researcher.analyze(analyst_reports, ticker='AAPL')

        assert result is not None
        assert result.get('stance') == 'bull'
        assert result.get('agent') == 'Bull Researcher'

    def test_analyze_bear_case(self, mock_llm_router):
        """Test bear case analysis"""
        researcher = ResearcherAgent(mock_llm_router, stance='bear')

        analyst_reports = {
            'market': {'recommendation': 'sell', 'success': True}
        }

        result = researcher.analyze(analyst_reports, ticker='AAPL')

        assert result is not None
        assert result.get('stance') == 'bear'
        assert result.get('agent') == 'Bear Researcher'

    def test_synthesize_debate(self, mock_llm_router):
        """Test debate synthesis"""
        researcher = ResearcherAgent(mock_llm_router, stance='bull')

        bull_analysis = {
            'bull_case_summary': 'Strong growth potential',
            'stance': 'bull',
            'conviction_level': 'high'
        }

        bear_analysis = {
            'bear_case_summary': 'Overvaluation concerns',
            'stance': 'bear',
            'conviction_level': 'medium'
        }

        result = researcher.synthesize_debate(bull_analysis, bear_analysis)

        assert result is not None
        assert result.get('synthesis') == True
        assert result.get('success') == True
