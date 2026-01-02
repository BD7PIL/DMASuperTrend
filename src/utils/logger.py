"""
日志工具模块
提供统一的日志配置和管理
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from loguru import logger
import json
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """JSON格式日志处理器"""
    
    def format(self, record):
        log_obj = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    debug: bool = False
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径
        json_format: 是否使用JSON格式
        debug: 是否启用调试模式
    """
    # 清除默认处理器
    logger.remove()
    
    # 设置日志级别
    level = "DEBUG" if debug else log_level.upper()
    
    # 控制台输出
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stdout,
        level=level,
        format=console_format,
        colorize=True
    )
    
    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        if json_format:
            # JSON格式
            logger.add(
                str(log_path),
                level=level,
                format=lambda record: json.dumps({
                    'time': datetime.now().isoformat(),
                    'level': record['level'].name,
                    'module': record['name'],
                    'function': record['function'],
                    'line': record['line'],
                    'message': record['message'],
                }, ensure_ascii=False),
                rotation="10 MB",
                retention="30 days",
                compression="zip"
            )
        else:
            # 文本格式
            logger.add(
                str(log_path),
                level=level,
                format=console_format,
                rotation="10 MB",
                retention="30 days",
                compression="zip"
            )
    
    return logger


class TradingLogger:
    """交易专用日志记录器"""
    
    def __init__(self, name: str = "TradingSystem"):
        self.logger = logger.bind(module=name)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self.logger.error(self._format_message(message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def trade(self, symbol: str, side: str, price: float, amount: float, **kwargs):
        """交易日志"""
        message = f"交易 {symbol} {side}: 价格={price:.4f}, 数量={amount:.6f}"
        self.logger.info(self._format_message(message, **kwargs))
    
    def signal(self, symbol: str, signal_type: str, **kwargs):
        """信号日志"""
        message = f"信号 {symbol}: {signal_type}"
        self.logger.info(self._format_message(message, **kwargs))
    
    def risk(self, message: str, **kwargs):
        """风控日志"""
        self.logger.warning(f"[风控] {self._format_message(message, **kwargs)}")
    
    def performance(self, metrics: dict):
        """性能指标日志"""
        message = "性能指标: " + ", ".join([f"{k}={v:.4f}" for k, v in metrics.items()])
        self.logger.info(message)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """格式化消息"""
        if kwargs:
            extra = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{message} | {extra}"
        return message


# 全局日志实例
trading_logger = TradingLogger()


def get_trading_logger(name: str = "TradingSystem") -> TradingLogger:
    """
    获取交易日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        TradingLogger: 交易日志记录器
    """
    return TradingLogger(name)