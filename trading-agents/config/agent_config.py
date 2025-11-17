"""
Agent Configuration Loader
Loads agent settings from YAML configuration file
"""
import os
import yaml
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for a single agent"""
    model: str
    temperature: float
    max_tokens: int
    description: str


@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_pct: float
    max_sector_pct: float
    portfolio_concentration_limit: int
    max_portfolio_risk_pct: float
    max_cfd_position_pct: float
    max_total_cfd_exposure_pct: float
    min_risk_reward_ratio: float


@dataclass
class ExecutionConfig:
    """Execution settings"""
    parallel_agents: bool
    timeout_seconds: int
    retry_on_failure: bool
    max_retries: int


@dataclass
class OutputConfig:
    """Output settings"""
    save_agent_outputs: bool
    output_directory: str
    format: str
    include_timestamps: bool
    include_cost_tracking: bool


class AgentConfigLoader:
    """Loads and manages agent configuration from YAML"""

    def __init__(self, config_path: str = None):
        """
        Initialize config loader

        Args:
            config_path: Path to YAML config file (default: config/agents.yaml)
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                'agents.yaml'
            )

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            print(f"⚠️  Warning: Config file not found at {self.config_path}")
            print("   Using default configuration")
            return self._default_config()
        except Exception as e:
            print(f"⚠️  Warning: Failed to load config: {e}")
            print("   Using default configuration")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration if YAML file not found"""
        return {
            'agents': {
                'portfolio_analyst': {
                    'model': 'gpt-4o-mini',
                    'temperature': 0.3,
                    'max_tokens': 1000,
                    'description': 'Portfolio analysis'
                },
                'orchestrator': {
                    'model': 'claude-3-5-sonnet',
                    'temperature': 0.5,
                    'max_tokens': 2500,
                    'description': 'Orchestration'
                }
            },
            'execution': {
                'parallel_agents': True,
                'timeout_seconds': 30,
                'retry_on_failure': True,
                'max_retries': 2
            }
        }

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Get configuration for specific agent

        Args:
            agent_name: Name of agent (e.g., 'portfolio_analyst')

        Returns:
            AgentConfig object
        """
        agent_config = self.config.get('agents', {}).get(agent_name, {})

        return AgentConfig(
            model=agent_config.get('model', 'gpt-4o-mini'),
            temperature=agent_config.get('temperature', 0.5),
            max_tokens=agent_config.get('max_tokens', 1000),
            description=agent_config.get('description', '')
        )

    def get_risk_config(self) -> RiskConfig:
        """Get risk management configuration"""
        risk_config = self.config.get('risk_config', {})

        return RiskConfig(
            max_position_pct=risk_config.get('max_position_pct', 15.0),
            max_sector_pct=risk_config.get('max_sector_pct', 40.0),
            portfolio_concentration_limit=risk_config.get('portfolio_concentration_limit', 3),
            max_portfolio_risk_pct=risk_config.get('max_portfolio_risk_pct', 2.0),
            max_cfd_position_pct=risk_config.get('max_cfd_position_pct', 5.0),
            max_total_cfd_exposure_pct=risk_config.get('max_total_cfd_exposure_pct', 20.0),
            min_risk_reward_ratio=risk_config.get('min_risk_reward_ratio', 1.5)
        )

    def get_execution_config(self) -> ExecutionConfig:
        """Get execution configuration"""
        exec_config = self.config.get('execution', {})

        return ExecutionConfig(
            parallel_agents=exec_config.get('parallel_agents', True),
            timeout_seconds=exec_config.get('timeout_seconds', 30),
            retry_on_failure=exec_config.get('retry_on_failure', True),
            max_retries=exec_config.get('max_retries', 2)
        )

    def get_output_config(self) -> OutputConfig:
        """Get output configuration"""
        output_config = self.config.get('output', {})

        return OutputConfig(
            save_agent_outputs=output_config.get('save_agent_outputs', True),
            output_directory=output_config.get('output_directory', 'outputs'),
            format=output_config.get('format', 'json'),
            include_timestamps=output_config.get('include_timestamps', True),
            include_cost_tracking=output_config.get('include_cost_tracking', True)
        )

    def get_model_cost(self, model_name: str) -> Dict[str, float]:
        """
        Get cost estimates for a model

        Args:
            model_name: Model name (e.g., 'gpt-4o-mini')

        Returns:
            Dict with 'input' and 'output' costs per 1M tokens
        """
        model_costs = self.config.get('model_costs', {})
        return model_costs.get(model_name, {'input': 0.0, 'output': 0.0})

    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        print("✓ Configuration reloaded")


# Global config instance
_config_loader = None


def get_config_loader() -> AgentConfigLoader:
    """Get global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = AgentConfigLoader()
    return _config_loader


# Example usage
if __name__ == "__main__":
    print("=== Agent Configuration Loader Test ===\n")

    loader = AgentConfigLoader()

    print("Portfolio Analyst Config:")
    pa_config = loader.get_agent_config('portfolio_analyst')
    print(f"  Model: {pa_config.model}")
    print(f"  Temperature: {pa_config.temperature}")
    print(f"  Max Tokens: {pa_config.max_tokens}")

    print("\nRisk Config:")
    risk = loader.get_risk_config()
    print(f"  Max Position: {risk.max_position_pct}%")
    print(f"  Max Sector: {risk.max_sector_pct}%")
    print(f"  Max CFD Position: {risk.max_cfd_position_pct}%")

    print("\nExecution Config:")
    exec_cfg = loader.get_execution_config()
    print(f"  Parallel Agents: {exec_cfg.parallel_agents}")
    print(f"  Timeout: {exec_cfg.timeout_seconds}s")

    print("\nModel Costs:")
    for model in ['gpt-4o-mini', 'claude-3-5-sonnet']:
        costs = loader.get_model_cost(model)
        print(f"  {model}: ${costs['input']:.2f}/${costs['output']:.2f} per 1M tokens")
