"""
Configuration Management Module

Loads and validates configuration from config.yaml
Provides type-safe access to configuration values
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class StrategyConfig:
    """Configuration for a single strategy"""
    enabled: bool
    base_risk_pct: float
    max_risk_pct: float
    max_positions: int
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradingConfig:
    """Trading configuration"""
    enabled: bool
    testnet: bool
    symbols: list
    strategies: Dict[str, StrategyConfig]
    risk_management: Dict[str, Any]


@dataclass
class DataConfig:
    """Data feed configuration"""
    provider: str
    websocket_url: str
    rest_api_url: str
    candle_interval: str
    buffer_size: int
    max_price_change_pct: float
    min_volume_threshold: float
    reconnect_attempts: int
    reconnect_delay_seconds: int
    max_reconnect_delay: int


@dataclass
class BingXConfig:
    """BingX API configuration"""
    api_key: str
    api_secret: str
    testnet: bool
    base_url: str
    requests_per_minute: int
    default_leverage: int
    fixed_position_value_usdt: float
    leverage_mode: str


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str
    console_output: bool
    file_output: bool
    file_path: str
    max_size_mb: int
    backup_count: int
    json_format: bool
    dashboard_interval_minutes: int


@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str
    path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class NotificationsConfig:
    """Email notifications configuration"""
    enabled: bool
    resend_api_key: str
    to_email: str
    notify_trade_opened: bool = True
    notify_trade_closed: bool = True
    notify_errors: bool = True
    notify_emergency_stop: bool = True
    notify_daily_summary: bool = True
    notify_bot_started: bool = True


@dataclass
class SafetyConfig:
    """Safety features configuration"""
    dry_run: bool
    stop_file: str
    emergency_stop_enabled: bool
    min_account_balance: float
    check_existing_positions: bool
    close_positions_on_shutdown: bool
    max_shutdown_wait_seconds: int


class Config:
    """
    Main configuration class

    Usage:
        config = Config('config.yaml')
        config.load()

        if config.trading.enabled:
            print(f"Trading on: {config.trading.symbols}")
    """

    def __init__(self, config_path: str = 'config.yaml'):
        self.config_path = Path(config_path)
        self.raw_config: Dict[str, Any] = {}

        # Configuration objects
        self.trading: Optional[TradingConfig] = None
        self.data: Optional[DataConfig] = None
        self.bingx: Optional[BingXConfig] = None
        self.logging: Optional[LoggingConfig] = None
        self.database: Optional[DatabaseConfig] = None
        self.notifications: Optional[NotificationsConfig] = None
        self.safety: Optional[SafetyConfig] = None

    def load(self) -> None:
        """Load and parse configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self.raw_config = yaml.safe_load(f)

        self._parse_config()
        self._validate_config()

    def _parse_config(self) -> None:
        """Parse raw config into typed objects"""

        # Parse trading config
        trading_cfg = self.raw_config['trading']
        strategies = {}

        for name, strategy_cfg in trading_cfg['strategies'].items():
            # Separate main params from strategy-specific params
            main_params = {
                'enabled', 'base_risk_pct', 'max_risk_pct', 'max_positions'
            }

            strategy_params = {
                k: v for k, v in strategy_cfg.items()
                if k not in main_params
            }

            strategies[name] = StrategyConfig(
                enabled=strategy_cfg['enabled'],
                base_risk_pct=strategy_cfg['base_risk_pct'],
                max_risk_pct=strategy_cfg['max_risk_pct'],
                max_positions=strategy_cfg['max_positions'],
                params=strategy_params
            )

        self.trading = TradingConfig(
            enabled=trading_cfg['enabled'],
            testnet=trading_cfg['testnet'],
            symbols=trading_cfg['symbols'],
            strategies=strategies,
            risk_management=trading_cfg['risk_management']
        )

        # Parse data config
        data_cfg = self.raw_config['data']
        self.data = DataConfig(
            provider=data_cfg['provider'],
            websocket_url=data_cfg['websocket_url'],
            rest_api_url=data_cfg['rest_api_url'],
            candle_interval=data_cfg['candle_interval'],
            buffer_size=data_cfg['buffer_size'],
            max_price_change_pct=data_cfg['max_price_change_pct'],
            min_volume_threshold=data_cfg['min_volume_threshold'],
            reconnect_attempts=data_cfg['reconnect_attempts'],
            reconnect_delay_seconds=data_cfg['reconnect_delay_seconds'],
            max_reconnect_delay=data_cfg['max_reconnect_delay']
        )

        # Parse BingX config - environment variables take precedence
        bingx_cfg = self.raw_config['bingx']

        # Get API keys from env vars first, then fall back to config file
        api_key = os.environ.get('BINGX_API_KEY') or bingx_cfg.get('api_key', '')
        api_secret = os.environ.get('BINGX_API_SECRET') or bingx_cfg.get('api_secret', '')

        # Handle ${VAR} placeholders in config
        if api_key.startswith('${') and api_key.endswith('}'):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, '')
        if api_secret.startswith('${') and api_secret.endswith('}'):
            env_var = api_secret[2:-1]
            api_secret = os.environ.get(env_var, '')

        self.bingx = BingXConfig(
            api_key=api_key,
            api_secret=api_secret,
            testnet=bingx_cfg['testnet'],
            base_url=bingx_cfg['base_url'],
            requests_per_minute=bingx_cfg['requests_per_minute'],
            default_leverage=bingx_cfg['default_leverage'],
            fixed_position_value_usdt=bingx_cfg.get('fixed_position_value_usdt', 0.0),
            leverage_mode=bingx_cfg['leverage_mode']
        )

        # Parse logging config
        log_cfg = self.raw_config['logging']
        self.logging = LoggingConfig(
            level=log_cfg['level'],
            console_output=log_cfg['console_output'],
            file_output=log_cfg['file_output'],
            file_path=log_cfg['file_path'],
            max_size_mb=log_cfg['max_size_mb'],
            backup_count=log_cfg['backup_count'],
            json_format=log_cfg['json_format'],
            dashboard_interval_minutes=log_cfg['dashboard_interval_minutes']
        )

        # Parse database config
        db_cfg = self.raw_config['database']
        self.database = DatabaseConfig(
            type=db_cfg['type'],
            path=db_cfg.get('path'),
            host=db_cfg.get('host'),
            port=db_cfg.get('port'),
            database=db_cfg.get('database'),
            user=db_cfg.get('user'),
            password=db_cfg.get('password'),
            echo=db_cfg.get('echo', False),
            pool_size=db_cfg.get('pool_size', 5),
            max_overflow=db_cfg.get('max_overflow', 10)
        )

        # Parse notifications config (optional)
        notif_cfg = self.raw_config.get('notifications', {})
        if notif_cfg:
            # Handle env var placeholders
            api_key = notif_cfg.get('resend_api_key', '')
            to_email = notif_cfg.get('to_email', '')

            if api_key.startswith('${') and api_key.endswith('}'):
                api_key = os.environ.get(api_key[2:-1], '')
            if to_email.startswith('${') and to_email.endswith('}'):
                to_email = os.environ.get(to_email[2:-1], '')

            # Also check direct env vars
            api_key = api_key or os.environ.get('RESEND_API_KEY', '')
            to_email = to_email or os.environ.get('NOTIFICATION_EMAIL', '')

            self.notifications = NotificationsConfig(
                enabled=notif_cfg.get('enabled', True),
                resend_api_key=api_key,
                to_email=to_email,
                notify_trade_opened=notif_cfg.get('notify_trade_opened', True),
                notify_trade_closed=notif_cfg.get('notify_trade_closed', True),
                notify_errors=notif_cfg.get('notify_errors', True),
                notify_emergency_stop=notif_cfg.get('notify_emergency_stop', True),
                notify_daily_summary=notif_cfg.get('notify_daily_summary', True),
                notify_bot_started=notif_cfg.get('notify_bot_started', True)
            )
        else:
            # Default disabled config
            self.notifications = NotificationsConfig(
                enabled=False,
                resend_api_key='',
                to_email=''
            )

        # Parse safety config
        safety_cfg = self.raw_config['safety']
        self.safety = SafetyConfig(
            dry_run=safety_cfg['dry_run'],
            stop_file=safety_cfg['stop_file'],
            emergency_stop_enabled=safety_cfg['emergency_stop_enabled'],
            min_account_balance=safety_cfg['min_account_balance'],
            check_existing_positions=safety_cfg['check_existing_positions'],
            close_positions_on_shutdown=safety_cfg['close_positions_on_shutdown'],
            max_shutdown_wait_seconds=safety_cfg['max_shutdown_wait_seconds']
        )

    def _validate_config(self) -> None:
        """Validate configuration values"""

        # Validate trading config
        if self.trading.enabled and not self.trading.symbols:
            raise ValueError("Trading enabled but no symbols configured")

        for name, strategy in self.trading.strategies.items():
            if strategy.enabled:
                if strategy.base_risk_pct <= 0 or strategy.base_risk_pct > 100:
                    raise ValueError(f"{name}: base_risk_pct must be > 0 and <= 100")
                if strategy.max_risk_pct < strategy.base_risk_pct:
                    raise ValueError(f"{name}: max_risk_pct must be >= base_risk_pct")
                if strategy.max_positions <= 0:
                    raise ValueError(f"{name}: max_positions must be > 0")

        # Validate risk management
        rm = self.trading.risk_management
        if rm['max_portfolio_risk'] <= 0:
            raise ValueError("max_portfolio_risk must be > 0")
        if rm['max_drawdown'] <= 0:
            raise ValueError("max_drawdown must be > 0")

        # Validate BingX config
        if self.trading.enabled and not self.safety.dry_run:
            if not self.bingx.api_key or self.bingx.api_key.startswith('${'):
                raise ValueError("BingX API key not configured. Set BINGX_API_KEY environment variable.")
            if not self.bingx.api_secret or self.bingx.api_secret.startswith('${'):
                raise ValueError("BingX API secret not configured. Set BINGX_API_SECRET environment variable.")

        # Validate database config
        if self.database.type == 'sqlite':
            if not self.database.path:
                raise ValueError("SQLite database path not configured")
        elif self.database.type == 'postgresql':
            required = ['host', 'port', 'database', 'user', 'password']
            for field in required:
                if not getattr(self.database, field):
                    raise ValueError(f"PostgreSQL {field} not configured")
        else:
            raise ValueError(f"Unsupported database type: {self.database.type}")

        # Validate logging
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level not in valid_levels:
            raise ValueError(f"Invalid log level: {self.logging.level}")

    def get_strategy_config(self, strategy_name: str) -> Optional[StrategyConfig]:
        """Get configuration for a specific strategy"""
        return self.trading.strategies.get(strategy_name)

    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """Check if a strategy is enabled"""
        strategy = self.get_strategy_config(strategy_name)
        return strategy is not None and strategy.enabled

    def get_database_url(self) -> str:
        """Get database connection URL"""
        if self.database.type == 'sqlite':
            return f"sqlite:///{self.database.path}"
        elif self.database.type == 'postgresql':
            return (f"postgresql://{self.database.user}:{self.database.password}"
                   f"@{self.database.host}:{self.database.port}/{self.database.database}")
        else:
            raise ValueError(f"Unsupported database type: {self.database.type}")

    def reload(self) -> None:
        """Reload configuration from file"""
        self.load()

    def __repr__(self) -> str:
        return (f"Config(trading_enabled={self.trading.enabled}, "
                f"symbols={self.trading.symbols}, "
                f"dry_run={self.safety.dry_run})")


# Global config instance (singleton pattern)
_config_instance: Optional[Config] = None


def load_config(config_path: str = 'config.yaml') -> Config:
    """Load configuration (singleton)"""
    global _config_instance

    if _config_instance is None:
        _config_instance = Config(config_path)
        _config_instance.load()

    return _config_instance


def get_config() -> Config:
    """Get loaded configuration instance"""
    global _config_instance

    if _config_instance is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")

    return _config_instance


if __name__ == "__main__":
    # Test configuration loading
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'

    print(f"Loading configuration from: {config_path}\n")

    try:
        config = Config(config_path)
        config.load()

        print("Configuration loaded successfully!")
        print(f"\nTrading: {config.trading.enabled}")
        print(f"Symbols: {config.trading.symbols}")
        print(f"Dry Run: {config.safety.dry_run}")
        print(f"\nEnabled Strategies:")

        for name, strategy in config.trading.strategies.items():
            if strategy.enabled:
                print(f"  - {name}: risk={strategy.base_risk_pct}%-{strategy.max_risk_pct}%, "
                      f"max_positions={strategy.max_positions}")

        print(f"\nDatabase: {config.database.type} ({config.get_database_url()})")
        print(f"Logging: {config.logging.level} -> {config.logging.file_path}")

    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
