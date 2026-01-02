"""
配置管理系统
负责加载和管理所有系统配置
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import yaml


# 加载环境变量
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str
    api_key: Optional[str] = None
    secret: Optional[str] = None
    password: Optional[str] = None
    sandbox: bool = True
    rate_limit: int = 100  # 每分钟最大请求数


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"  # sqlite, postgresql, mysql
    host: str = "localhost"
    port: int = 5432
    username: str = ""
    password: str = ""
    database: str = "dmasupertrend"
    redis_url: str = "redis://localhost:6379/0"


@dataclass
class StrategyConfig:
    """策略配置"""
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    fast_ma: int = 9
    slow_ma: int = 21
    super_trend_period: int = 10
    super_trend_multiplier: float = 3.0
    risk_per_trade: float = 0.02  # 单笔风险2%
    max_daily_loss: float = 0.05  # 日最大亏损5%


@dataclass
class RiskConfig:
    """风控配置"""
    max_leverage: int = 20
    min_leverage: int = 3
    max_position_size: float = 0.3  # 单币种最大30%
    stop_loss_percent: float = 0.02  # 硬止损2%
    take_profit_1: float = 1.5  # 第一批止盈1.5倍
    take_profit_2: float = 2.0  # 第二批止盈2.0倍
    trailing_stop: float = 0.03  # 移动止盈回撤3%
    max_consecutive_losses: int = 3  # 熔断机制


@dataclass
class TelegramConfig:
    """Telegram配置"""
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    notify_open: bool = True
    notify_close: bool = True
    notify_stop: bool = True
    report_interval: int = 3600  # 每小时报告


@dataclass
class BacktestConfig:
    """回测配置"""
    parallel_workers: int = 4
    cache_ttl: int = 3600
    optimize_iterations: int = 100
    train_test_split: float = 0.8


@dataclass
class SystemConfig:
    """系统总配置"""
    exchange: ExchangeConfig
    database: DatabaseConfig
    strategy: StrategyConfig
    risk: RiskConfig
    telegram: TelegramConfig
    backtest: BacktestConfig
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/trading.log"
    
    # 性能配置
    max_memory_usage: float = 2.0  # GB
    data_delay_ms: int = 500
    order_delay_ms: int = 100
    
    # 开发环境
    debug: bool = False


def load_config(config_path: Optional[str] = None) -> SystemConfig:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，None则使用默认配置
        
    Returns:
        SystemConfig: 系统配置对象
    """
    # 默认配置
    config = {
        'exchange': {
            'name': 'okx',
            'sandbox': True,
            'rate_limit': 100
        },
        'database': {
            'type': 'sqlite',
            'database': 'dmasupertrend.db',
            'redis_url': 'redis://localhost:6379/0'
        },
        'strategy': {
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'fast_ma': 9,
            'slow_ma': 21,
            'super_trend_period': 10,
            'super_trend_multiplier': 3.0,
            'risk_per_trade': 0.02,
            'max_daily_loss': 0.05
        },
        'risk': {
            'max_leverage': 20,
            'min_leverage': 3,
            'max_position_size': 0.3,
            'stop_loss_percent': 0.02,
            'take_profit_1': 1.5,
            'take_profit_2': 2.0,
            'trailing_stop': 0.03,
            'max_consecutive_losses': 3
        },
        'telegram': {
            'enabled': False,
            'notify_open': True,
            'notify_close': True,
            'notify_stop': True,
            'report_interval': 3600
        },
        'backtest': {
            'parallel_workers': 4,
            'cache_ttl': 3600,
            'optimize_iterations': 100,
            'train_test_split': 0.8
        },
        'log_level': 'INFO',
        'log_file': 'logs/trading.log',
        'max_memory_usage': 2.0,
        'data_delay_ms': 500,
        'order_delay_ms': 100,
        'debug': False
    }
    
    # 从环境变量覆盖配置
    exchange_config = config['exchange']
    exchange_config['api_key'] = os.getenv('OKX_API_KEY')
    exchange_config['secret'] = os.getenv('OKX_SECRET')
    exchange_config['password'] = os.getenv('OKX_PASSWORD')
    
    telegram_config = config['telegram']
    telegram_config['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_config['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
    
    # 如果指定了配置文件，从文件加载
    if config_path:
        config_path = Path(config_path)
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                # 合并配置
                for key, value in file_config.items():
                    if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                        config[key].update(value)
                    else:
                        config[key] = value
    
    # 创建配置对象
    system_config = SystemConfig(
        exchange=ExchangeConfig(**config['exchange']),
        database=DatabaseConfig(**config['database']),
        strategy=StrategyConfig(**config['strategy']),
        risk=RiskConfig(**config['risk']),
        telegram=TelegramConfig(**config['telegram']),
        backtest=BacktestConfig(**config['backtest']),
        log_level=config['log_level'],
        log_file=config['log_file'],
        max_memory_usage=config['max_memory_usage'],
        data_delay_ms=config['data_delay_ms'],
        order_delay_ms=config['order_delay_ms'],
        debug=config['debug']
    )
    
    return system_config


def save_config(config: SystemConfig, config_path: str) -> None:
    """
    保存配置到文件
    
    Args:
        config: 系统配置对象
        config_path: 保存路径
    """
    config_dict = {
        'exchange': {
            'name': config.exchange.name,
            'sandbox': config.exchange.sandbox,
            'rate_limit': config.exchange.rate_limit
        },
        'database': {
            'type': config.database.type,
            'host': config.database.host,
            'port': config.database.port,
            'database': config.database.database,
            'redis_url': config.database.redis_url
        },
        'strategy': {
            'symbol': config.strategy.symbol,
            'timeframe': config.strategy.timeframe,
            'fast_ma': config.strategy.fast_ma,
            'slow_ma': config.strategy.slow_ma,
            'super_trend_period': config.strategy.super_trend_period,
            'super_trend_multiplier': config.strategy.super_trend_multiplier,
            'risk_per_trade': config.strategy.risk_per_trade,
            'max_daily_loss': config.strategy.max_daily_loss
        },
        'risk': {
            'max_leverage': config.risk.max_leverage,
            'min_leverage': config.risk.min_leverage,
            'max_position_size': config.risk.max_position_size,
            'stop_loss_percent': config.risk.stop_loss_percent,
            'take_profit_1': config.risk.take_profit_1,
            'take_profit_2': config.risk.take_profit_2,
            'trailing_stop': config.risk.trailing_stop,
            'max_consecutive_losses': config.risk.max_consecutive_losses
        },
        'telegram': {
            'enabled': config.telegram.enabled,
            'notify_open': config.telegram.notify_open,
            'notify_close': config.telegram.notify_close,
            'notify_stop': config.telegram.notify_stop,
            'report_interval': config.telegram.report_interval
        },
        'backtest': {
            'parallel_workers': config.backtest.parallel_workers,
            'cache_ttl': config.backtest.cache_ttl,
            'optimize_iterations': config.backtest.optimize_iterations,
            'train_test_split': config.backtest.train_test_split
        },
        'log_level': config.log_level,
        'log_file': config.log_file,
        'max_memory_usage': config.max_memory_usage,
        'data_delay_ms': config.data_delay_ms,
        'order_delay_ms': config.order_delay_ms,
        'debug': config.debug
    }
    
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)