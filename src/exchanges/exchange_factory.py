"""
交易所工厂
根据配置创建和管理交易所实例
"""

import os
from typing import Dict, Optional, Any
import logging

from .exchange_interface import ExchangeInterface
from .okx_adapter import OKXAdapter
from src.config import settings


class ExchangeFactory:
    """交易所工厂类"""
    
    _instances: Dict[str, ExchangeInterface] = {}
    _logger = logging.getLogger(__name__)
    
    # 支持的交易所映射
    EXCHANGE_MAP = {
        'okx': OKXAdapter,
        # 'binance': BinanceAdapter,  # TODO: 未来实现
        # 'bitget': BitgetAdapter,    # TODO: 未来实现
    }
    
    @classmethod
    def create_exchange(cls, exchange_name: str, config: Optional[Dict[str, Any]] = None) -> ExchangeInterface:
        """
        创建交易所实例
        
        Args:
            exchange_name: 交易所名称 ('okx', 'binance', 'bitget')
            config: 配置参数字典
            
        Returns:
            交易所适配器实例
            
        Raises:
            ValueError: 不支持的交易所类型
            Exception: 创建失败
        """
        exchange_name = exchange_name.lower()
        
        # 检查是否已存在实例
        cache_key = f"{exchange_name}_{hash(str(config))}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # 检查是否支持该交易所
        if exchange_name not in cls.EXCHANGE_MAP:
            raise ValueError(
                f"不支持的交易所: {exchange_name}。"
                f"支持的交易所: {list(cls.EXCHANGE_MAP.keys())}"
            )
        
        # 获取配置
        if config is None:
            config = cls._get_default_config(exchange_name)
        
        try:
            adapter_class = cls.EXCHANGE_MAP[exchange_name]
            
            # 创建适配器实例
            if exchange_name == 'okx':
                instance = adapter_class(
                    api_key=config.get('api_key'),
                    secret=config.get('secret'),
                    password=config.get('password'),
                    sandbox=config.get('sandbox', True)
                )
            else:
                instance = adapter_class(**config)
            
            # 缓存实例
            cls._instances[cache_key] = instance
            
            cls._logger.info(f"成功创建 {exchange_name} 交易所实例")
            return instance
            
        except Exception as e:
            cls._logger.error(f"创建 {exchange_name} 交易所实例失败: {e}")
            raise
    
    @classmethod
    def _get_default_config(cls, exchange_name: str) -> Dict[str, Any]:
        """
        获取默认配置
        
        Args:
            exchange_name: 交易所名称
            
        Returns:
            配置字典
        """
        # 从环境变量获取配置
        if exchange_name == 'okx':
            return {
                'api_key': os.getenv('OKX_API_KEY'),
                'secret': os.getenv('OKX_SECRET'),
                'password': os.getenv('OKX_PASSWORD'),
                'sandbox': os.getenv('OKX_SANDBOX', 'true').lower() == 'true',
            }
        
        # TODO: 其他交易所的默认配置
        return {}
    
    @classmethod
    def get_exchange(cls, exchange_name: str, config: Optional[Dict[str, Any]] = None) -> ExchangeInterface:
        """
        获取交易所实例（单例模式）
        
        Args:
            exchange_name: 交易所名称
            config: 配置参数
            
        Returns:
            交易所实例
        """
        return cls.create_exchange(exchange_name, config)
    
    @classmethod
    def get_all_instances(cls) -> Dict[str, ExchangeInterface]:
        """获取所有交易所实例"""
        return cls._instances.copy()
    
    @classmethod
    def remove_instance(cls, exchange_name: str, config: Optional[Dict[str, Any]] = None):
        """移除交易所实例"""
        cache_key = f"{exchange_name}_{hash(str(config))}"
        if cache_key in cls._instances:
            del cls._instances[cache_key]
            cls._logger.info(f"移除 {exchange_name} 交易所实例")
    
    @classmethod
    async def disconnect_all(cls):
        """断开所有交易所连接"""
        for name, instance in cls._instances.items():
            try:
                await instance.disconnect()
                cls._logger.info(f"断开 {name} 连接")
            except Exception as e:
                cls._logger.error(f"断开 {name} 连接失败: {e}")
        
        cls._instances.clear()
    
    @classmethod
    def get_supported_exchanges(cls) -> list:
        """获取支持的交易所列表"""
        return list(cls.EXCHANGE_MAP.keys())
    
    @classmethod
    def validate_config(cls, exchange_name: str, config: Dict[str, Any]) -> bool:
        """
        验证配置是否完整
        
        Args:
            exchange_name: 交易所名称
            config: 配置字典
            
        Returns:
            是否有效
        """
        exchange_name = exchange_name.lower()
        
        if exchange_name == 'okx':
            required = ['api_key', 'secret', 'password']
            return all(key in config for key in required)
        
        # TODO: 其他交易所的配置验证
        return True
    
    @classmethod
    def create_mock_exchange(cls, exchange_name: str = 'okx') -> ExchangeInterface:
        """
        创建模拟交易所实例（用于测试）
        
        Args:
            exchange_name: 交易所名称
            
        Returns:
            模拟交易所实例
        """
        from unittest.mock import Mock
        
        # 创建Mock适配器
        mock_adapter = Mock(spec=ExchangeInterface)
        
        # 设置基本的Mock行为
        mock_adapter.get_exchange_name.return_value = f"Mock_{exchange_name}"
        mock_adapter.is_connected.return_value = True
        mock_adapter.connect = Mock(return_value=True)
        mock_adapter.disconnect = Mock(return_value=True)
        
        # Mock数据方法
        mock_adapter.get_balance.return_value = {
            'USDT': {'free': 10000.0, 'used': 0.0, 'total': 10000.0}
        }
        
        mock_adapter.get_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'last': 50000.0,
            'bid': 49999.0,
            'ask': 50001.0,
            'volume': 1000.0,
        }
        
        mock_adapter.get_candles.return_value = [
            {
                'timestamp': 1640995200000,
                'open': 48000.0,
                'high': 49000.0,
                'low': 47500.0,
                'close': 48500.0,
                'volume': 100.0,
            }
        ]
        
        mock_adapter.create_order.return_value = {
            'order_id': 'mock_order_123',
            'status': 'open',
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'amount': 0.1,
            'price': 50000.0,
        }
        
        mock_adapter.get_open_orders.return_value = []
        mock_adapter.get_positions.return_value = []
        
        return mock_adapter</parameter>
</write_to_file>