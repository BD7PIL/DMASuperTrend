"""
交易所统一接口
定义所有交易所必须实现的标准接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
import asyncio


class ExchangeInterface(ABC):
    """交易所统一接口"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接交易所"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接"""
        pass
    
    @abstractmethod
    async def get_balance(self, currency: str = None) -> Dict[str, Any]:
        """
        获取账户余额
        
        Args:
            currency: 币种，None表示获取所有币种
            
        Returns:
            余额信息字典
        """
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取ticker信息
        
        Args:
            symbol: 交易对，如'BTC/USDT'
            
        Returns:
            ticker信息字典
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        获取订单簿
        
        Args:
            symbol: 交易对
            limit: 深度数量
            
        Returns:
            订单簿信息字典
        """
        pass
    
    @abstractmethod
    async def get_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对
            timeframe: 时间框架，如'1m', '5m', '1h', '4h', '1d'
            limit: K线数量
            
        Returns:
            K线数据列表
        """
        pass
    
    @abstractmethod
    async def create_order(self, symbol: str, side: str, order_type: str, 
                          amount: float, price: Optional[float] = None, 
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建订单
        
        Args:
            symbol: 交易对
            side: 买卖方向，'buy'或'sell'
            order_type: 订单类型，'market'或'limit'
            amount: 数量
            price: 价格（限价单需要）
            params: 额外参数
            
        Returns:
            订单信息字典
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            symbol: 交易对
            
        Returns:
            取消结果字典
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        获取未成交订单
        
        Args:
            symbol: 交易对，None表示所有交易对
            
        Returns:
            订单列表
        """
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        获取订单详情
        
        Args:
            order_id: 订单ID
            symbol: 交易对
            
        Returns:
            订单详情字典
        """
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        获取持仓信息
        
        Args:
            symbol: 交易对，None表示所有持仓
            
        Returns:
            持仓列表
        """
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        设置杠杆
        
        Args:
            symbol: 交易对
            leverage: 杠杆倍数
            
        Returns:
            设置结果字典
        """
        pass
    
    @abstractmethod
    async def get_fee(self, symbol: str) -> Dict[str, float]:
        """
        获取交易费率
        
        Args:
            symbol: 交易对
            
        Returns:
            费率信息字典
        """
        pass
    
    @abstractmethod
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接"""
        pass</parameter>
</write_to_file>