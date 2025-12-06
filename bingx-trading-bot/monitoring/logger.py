"""
Structured Logging

Configures and provides structured logging for the trading engine
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging

    Outputs logs as JSON for easy parsing and analysis
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add custom fields from extra
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info']:
                log_data[key] = value

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter

    Adds colors to console output for better readability
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format: [TIMESTAMP] LEVEL - message
        record.levelname = f"{color}{record.levelname}{reset}"

        return super().format(record)


def setup_logging(
    level: str = 'INFO',
    console_output: bool = True,
    file_output: bool = True,
    file_path: str = './logs/trading-engine.log',
    max_size_mb: int = 50,
    backup_count: int = 5,
    json_format: bool = False
) -> None:
    """
    Configure logging for the trading engine

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Enable console output
        file_output: Enable file output
        file_path: Path to log file
        max_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep
        json_format: Use JSON format for logs
    """

    # Create logs directory if it doesn't exist
    log_path = Path(file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if json_format:
            console_formatter = JSONFormatter()
        else:
            console_formatter = ColoredFormatter(
                '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if file_output:
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)

        if json_format:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)-8s - %(name)-25s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Log initial message
    root_logger.info(f"Logging configured: level={level}, console={console_output}, "
                    f"file={file_output}, json={json_format}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Trading-specific logging helpers
def log_trade_entry(logger: logging.Logger, strategy: str, symbol: str,
                    side: str, price: float, quantity: float, **kwargs) -> None:
    """Log trade entry"""
    logger.info(
        f"TRADE ENTRY: {strategy} {side} {symbol} @ {price:.8f} | qty={quantity:.4f}",
        extra={
            'event_type': 'trade_entry',
            'strategy': strategy,
            'symbol': symbol,
            'side': side,
            'price': price,
            'quantity': quantity,
            **kwargs
        }
    )


def log_trade_exit(logger: logging.Logger, strategy: str, symbol: str,
                   side: str, entry_price: float, exit_price: float,
                   pnl_pct: float, exit_reason: str, **kwargs) -> None:
    """Log trade exit"""
    logger.info(
        f"TRADE EXIT: {strategy} {side} {symbol} @ {exit_price:.8f} | "
        f"PnL: {pnl_pct:+.2f}% | Reason: {exit_reason}",
        extra={
            'event_type': 'trade_exit',
            'strategy': strategy,
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            **kwargs
        }
    )


def log_signal(logger: logging.Logger, strategy: str, symbol: str,
               signal_type: str, price: float, **kwargs) -> None:
    """Log trading signal"""
    logger.info(
        f"SIGNAL: {strategy} {signal_type} {symbol} @ {price:.8f}",
        extra={
            'event_type': 'signal',
            'strategy': strategy,
            'symbol': symbol,
            'signal_type': signal_type,
            'price': price,
            **kwargs
        }
    )


def log_system_event(logger: logging.Logger, event: str, severity: str,
                     message: str, **kwargs) -> None:
    """Log system event"""
    log_func = getattr(logger, severity.lower(), logger.info)
    log_func(
        f"SYSTEM: {event} - {message}",
        extra={
            'event_type': 'system',
            'system_event': event,
            **kwargs
        }
    )
