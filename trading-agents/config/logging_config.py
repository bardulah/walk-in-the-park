"""
Centralized logging configuration for trading agents system
Provides structured logging with multiple handlers and formatters
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Logging levels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter with color coding for console output
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        # Format the message
        formatted = super().format(record)

        return formatted


def setup_logging(
    name: str = "trading_agents",
    level: int = INFO,
    log_to_file: bool = False,
    log_dir: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Configure and return a logger with standardized formatting

    Args:
        name: Logger name (typically module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file in addition to console
        log_dir: Directory for log files (defaults to ./logs)
        use_colors: Whether to use colored output for console

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logging(__name__, level=DEBUG)
        >>> logger.info("System started")
        >>> logger.error("Error occurred", exc_info=True)
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Formatters
    if use_colors:
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_to_file:
        # Create logs directory if it doesn't exist
        log_dir_path = Path(log_dir or "logs")
        log_dir_path.mkdir(parents=True, exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir_path / f"{name}_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(level)

        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_file}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with standard configuration

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name) if logging.getLogger(name).handlers else setup_logging(name)


# Create default logger for the package
default_logger = setup_logging("trading_agents", level=INFO)


# Convenience functions for quick logging
def log_agent_start(agent_name: str, model: str, logger: Optional[logging.Logger] = None):
    """Log agent analysis start"""
    log = logger or default_logger
    log.info(f"🚀 {agent_name} starting analysis | Model: {model}")


def log_agent_complete(agent_name: str, duration_seconds: float, logger: Optional[logging.Logger] = None):
    """Log agent analysis completion"""
    log = logger or default_logger
    log.info(f"✅ {agent_name} completed in {duration_seconds:.2f}s")


def log_llm_call(model: str, tokens: int, cost: float, logger: Optional[logging.Logger] = None):
    """Log LLM API call"""
    log = logger or default_logger
    log.debug(f"💰 LLM call | Model: {model} | Tokens: {tokens} | Cost: ${cost:.4f}")


def log_error(error: Exception, context: str = "", logger: Optional[logging.Logger] = None):
    """Log error with context"""
    log = logger or default_logger
    log.error(f"❌ Error in {context}: {str(error)}", exc_info=True)


def log_cost_summary(total_cost: float, call_count: int, logger: Optional[logging.Logger] = None):
    """Log cost summary"""
    log = logger or default_logger
    log.info(f"💵 Cost Summary | Total: ${total_cost:.4f} | Calls: {call_count}")
