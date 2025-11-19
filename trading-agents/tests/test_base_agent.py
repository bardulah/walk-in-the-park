"""
Tests for BaseAgent class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
from agents.base_agent import BaseAgent


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing"""

    def get_system_prompt(self) -> str:
        return "Test system prompt"

    def analyze(self, *args, **kwargs) -> Dict[str, Any]:
        """Simple implementation for testing"""
        return {"result": "test"}


class TestBaseAgentInitialization:
    """Test BaseAgent initialization"""

    def test_init_with_all_params(self, mock_llm_router):
        """Test initialization with all parameters"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model",
            temperature=0.7,
            max_tokens=1000,
            agent_name="Test Agent"
        )

        assert agent.llm_router == mock_llm_router
        assert agent.model == "test-model"
        assert agent.temperature == 0.7
        assert agent.max_tokens == 1000
        assert agent.agent_name == "Test Agent"
        assert agent.logger is not None

    def test_init_with_defaults(self, mock_llm_router):
        """Test initialization with default values"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        assert agent.temperature == 0.5  # default
        assert agent.max_tokens == 2000  # default
        assert agent.agent_name == "ConcreteAgent"  # class name

    def test_logger_created(self, mock_llm_router):
        """Test that logger is properly created"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model",
            agent_name="Test Agent"
        )

        assert hasattr(agent, 'logger')
        assert agent.logger is not None


class TestLLMCalling:
    """Test LLM calling functionality"""

    def test_call_llm_success(self, mock_llm_router):
        """Test successful LLM call"""
        mock_llm_router.call.return_value = '{"success": true}'

        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        response = agent._call_llm(
            system_prompt="System prompt",
            user_prompt="User prompt"
        )

        assert response == '{"success": true}'
        mock_llm_router.call.assert_called_once()

    def test_call_llm_with_custom_params(self, mock_llm_router):
        """Test LLM call with custom temperature and max_tokens"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model",
            temperature=0.5,
            max_tokens=1500
        )

        agent._call_llm(
            system_prompt="System",
            user_prompt="User",
            temperature=0.8,
            max_tokens=2500
        )

        # Verify custom params were passed
        call_args = mock_llm_router.call.call_args
        assert call_args[1]['temperature'] == 0.8
        assert call_args[1]['max_tokens'] == 2500

    def test_call_llm_uses_defaults(self, mock_llm_router):
        """Test LLM call uses default params when not specified"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model",
            temperature=0.3,
            max_tokens=1000
        )

        agent._call_llm(
            system_prompt="System",
            user_prompt="User"
        )

        # Verify defaults were used
        call_args = mock_llm_router.call.call_args
        assert call_args[1]['temperature'] == 0.3
        assert call_args[1]['max_tokens'] == 1000

    def test_call_llm_failure_raises_runtime_error(self, mock_llm_router):
        """Test LLM call failure raises RuntimeError"""
        mock_llm_router.call.side_effect = Exception("API Error")

        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        with pytest.raises(RuntimeError, match="LLM call failed"):
            agent._call_llm(
                system_prompt="System",
                user_prompt="User"
            )


class TestJSONParsing:
    """Test JSON parsing functionality"""

    def test_parse_valid_json(self, mock_llm_router):
        """Test parsing valid JSON response"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        response = '{"key": "value", "number": 42}'
        result = agent._parse_json_response(response)

        assert result["key"] == "value"
        assert result["number"] == 42

    def test_parse_with_default(self, mock_llm_router):
        """Test parsing with default fallback"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        default = {"error": "parsing failed"}
        result = agent._parse_json_response("Not JSON", default=default)

        assert result == default

    def test_parse_without_default_raises(self, mock_llm_router):
        """Test parsing without default raises ValueError"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        with pytest.raises(ValueError):
            agent._parse_json_response("Not JSON")


class TestLoggingMethods:
    """Test logging methods"""

    def test_log_progress(self, mock_llm_router, capsys):
        """Test progress logging"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model",
            agent_name="Test Agent"
        )

        agent._log_progress("Starting analysis", emoji="🚀")

        captured = capsys.readouterr()
        assert "🚀 Test Agent: Starting analysis" in captured.out
        assert "Model: test-model" in captured.out

    def test_log_info(self, mock_llm_router, capsys):
        """Test info logging"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        agent._log_info("Information message")

        captured = capsys.readouterr()
        assert "Information message" in captured.out

    def test_log_warning(self, mock_llm_router, capsys):
        """Test warning logging"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        agent._log_warning("Warning message")

        captured = capsys.readouterr()
        assert "⚠️  Warning message" in captured.out

    def test_log_error(self, mock_llm_router, capsys):
        """Test error logging"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model"
        )

        agent._log_error("Error message")

        captured = capsys.readouterr()
        assert "❌ Error message" in captured.out


class TestErrorResponse:
    """Test error response building"""

    def test_build_error_response(self, mock_llm_router):
        """Test building standardized error response"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="test-model",
            agent_name="Test Agent"
        )

        error = Exception("Something went wrong")
        response = agent._build_error_response(error, "TEST_ERROR")

        assert response["error"] == "TEST_ERROR"
        assert response["message"] == "Something went wrong"
        assert response["agent"] == "Test Agent"
        assert response["success"] is False


class TestAbstractMethods:
    """Test abstract method enforcement"""

    def test_cannot_instantiate_base_agent_directly(self, mock_llm_router):
        """Test that BaseAgent cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseAgent(
                llm_router=mock_llm_router,
                model="test-model"
            )

    def test_concrete_agent_must_implement_analyze(self, mock_llm_router):
        """Test that concrete agents must implement analyze()"""

        class IncompleteAgent(BaseAgent):
            def get_system_prompt(self) -> str:
                return "prompt"
            # Missing analyze() implementation

        with pytest.raises(TypeError):
            IncompleteAgent(
                llm_router=mock_llm_router,
                model="test-model"
            )

    def test_concrete_agent_must_implement_get_system_prompt(self, mock_llm_router):
        """Test that concrete agents must implement get_system_prompt()"""

        class IncompleteAgent(BaseAgent):
            def analyze(self, *args, **kwargs) -> Dict[str, Any]:
                return {}
            # Missing get_system_prompt() implementation

        with pytest.raises(TypeError):
            IncompleteAgent(
                llm_router=mock_llm_router,
                model="test-model"
            )


class TestRepr:
    """Test string representation"""

    def test_repr(self, mock_llm_router):
        """Test __repr__ method"""
        agent = ConcreteAgent(
            llm_router=mock_llm_router,
            model="gpt-4o-mini",
            temperature=0.7,
            agent_name="Test Agent"
        )

        repr_str = repr(agent)
        assert "Test Agent" in repr_str
        assert "gpt-4o-mini" in repr_str
        assert "0.7" in repr_str
