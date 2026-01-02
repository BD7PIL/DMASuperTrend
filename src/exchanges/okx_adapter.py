"""
OKX交易所适配器
实现OKX交易所的统一接口
"""

import ccxt
import asyncio
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging
from datetime import datetime
import aiohttp

from .exchange_interface import ExchangeInterface
from src.utils.decorators import retry, timeout


class OKXAdapter(ExchangeInterface):
    """OKX交易所适配器"""
    
    def __init__(self, api_key: str = None, secret: str = None, 
                 password: str = None, sandbox: bool = True):
        """
        初始化OKX适配器
        
        Args:
            api_key: API密钥
            secret: API密钥密钥
            password: API密码
            sandbox: 是否使用模拟环境
        """
        self.api_key = api_key
        self.secret = secret
        self.password = password
        self.sandbox = sandbox
        
        self.exchange = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
        # 初始化ccxt的OKX实例
        self._init_exchange()
    
    def _init_exchange(self):
        """初始化交易所实例"""
        try:
            config = {
                'exchange': 'okx',
                'sandbox': self.sandbox,
                'options': {
                    'defaultType': 'spot',  # 默认现货
                    'adjustForTimeDifference': True,
                }
            }
            
            # 如果提供了API凭证，配置认证
            if self.api_key and self.secret and self.password:
                config.update({
                    'apiKey': self.api_key,
                    'secret': self.secret,
                    'password': self.password,
                })
            
            self.exchange = ccxt.okx(config)
            self.logger.info(f"OKX交易所初始化完成 - 模式: {'模拟' if self.sandbox else '实盘'}")
            
        except Exception as e:
            self.logger.error(f"OKX交易所初始化失败: {e}")
            raise
    
    @retry(max_attempts=3, delay=1)
    @timeout(30)
    async def connect(self) -> bool:
        """连接交易所"""
        try:
            if not self.exchange:
                self._init_exchange()
            
            # 测试连接 - 获取服务器时间
            await asyncio.to_thread(self.exchange.load_markets)
            
            self.connected = True
            self.logger.info("OKX交易所连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"OKX连接失败: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """断开连接"""
        try:
            self.connected = False
            if self.exchange:
                self.exchange.close()
            self.logger.info("OKX交易所断开连接")
            return True
        except Exception as e:
            self.logger.error(f"OKX断开连接失败: {e}")
            return False
    
    @retry(max_attempts=3, delay=1)
    @timeout(30)
    async def get_balance(self, currency: str = None) -> Dict[str, Any]:
        """获取账户余额"""
        try:
            if not self.connected:
                await self.connect()
            
            balance = await asyncio.to_thread(self.exchange.fetch_balance)
            
            if currency:
                # 返回指定币种余额
                currency_upper = currency.upper()
                return {
                    'currency': currency_upper,
                    'free': balance['free'].get(currency_upper, 0),
                    'used': balance['used'].get(currency_upper, 0),
                    'total': balance['total'].get(currency_upper, 0),
                }
            
            # 返回所有币种余额
            return balance
            
        except Exception as e:
            self.logger.error(f"获取余额失败: {e}")
            raise
    
    @retry(max_attempts=3, delay=1)
    @timeout(30)
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取ticker信息"""
        try:
            if not self.connected:
                await self.connect()
            
            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            
            return {
                'symbol': symbol,
                'timestamp': ticker['timestamp'],
                'datetime': ticker['datetime'],
                'high': ticker['high'],
                'low': ticker['low'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'volume': ticker['baseVolume'],
                'quote_volume': ticker['quoteVolume'],
            }
            
        except Exception as e:
            self.logger.error(f"获取ticker失败: {e}")
            raise
    
    @retry(max_attempts=3, delay=1)
    @timeout(30)
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """获取订单簿"""
        try:
            if not self.connected:
                await self.connect()
            
            orderbook = await asyncio.to_thread(self.exchange.fetch_order_book, symbol, limit)
            
            return {
                'symbol': symbol,
                'timestamp': orderbook['timestamp'],
                'datetime': orderbook['datetime'],
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit],
            }
            
        except Exception as e:
            self.logger.error(f"获取订单簿失败: {e}")
            raise
    
    @retry(max_attempts=3, delay=1)
    @timeout(60)
    async def get_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取K线数据"""
        try:
            if not self.connected:
                await self.connect()
            
            # 时间框架映射
            timeframe_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W',
            }
            
            tf = timeframe_map.get(timeframe, timeframe)
            
            candles = await asyncio.to_thread(
                self.exchange.fetch_ohlcv, 
                symbol, 
                tf, 
                limit=limit
            )
            
            result = []
            for candle in candles:
                result.append({
                    'timestamp': candle[0],
                    'datetime': datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5],
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取K线数据失败: {e}")
            raise
    
    @retry(max_attempts=3, delay=2)
    @timeout(60)
    async def create_order(self, symbol: str, side: str, order_type: str, 
                          amount: float, price: Optional[float] = None, 
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建订单"""
        try:
            if not self.connected:
                await self.connect()
            
            # 验证参数
            if order_type == 'limit' and price is None:
                raise ValueError("限价单必须提供价格")
            
            # 订单类型映射
            type_map = {
                'market': 'market',
                'limit': 'limit',
            }
            
            order = {
                'symbol': symbol,
                'type': type_map.get(order_type, order_type),
                'side': side,
                'amount': amount,
            }
            
            if price:
                order['price'] = price
            
            if params:
                order.update(params)
            
            result = await asyncio.to_thread(self.exchange.create_order, **order)
            
            return {
                'order_id': result['id'],
                'symbol': result['symbol'],
                'type': result['type'],
                'side': result['side'],
                'price': result['price'],
                'amount': result['amount'],
                'filled': result['filled'],
                'remaining': result['remaining'],
                'status': result['status'],
                'timestamp': result['timestamp'],
            }
            
        except Exception as e:
            self.logger.error(f"创建订单失败: {e}")
            raise
    
    @retry(max_attempts=3, delay=1)
    @timeout(30)
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """取消订单"""
        try:
            if not self.connected:
                await self.connect()
            
            result = await asyncio.to_thread(
                self.exchange.cancel_order, 
                order_id, 
                symbol
            )
            
            return {
                'order_id': result['id'],
                'symbol': result['symbol'],
                'status': result['status'],
                'info': result,
            }
            
        except Exception as e:
            self.logger.error(f"取消订单失败: {e}")
            raise
    
    @retry(max_attempts=2, delay=1)
    @timeout(30)
    async def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """获取未成交订单"""
        try:
            if not self.connected:
                await self.connect()
            
            orders = await asyncio.to_thread(
                self.exchange.fetch_open_orders, 
                symbol
            )
            
            result = []
            for order in orders:
                result.append({
                    'order_id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'price': order['price'],
                    'amount': order['amount'],
                    'filled': order['filled'],
                    'remaining': order['remaining'],
                    'status': order['status'],
                    'timestamp': order['timestamp'],
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取未成交订单失败: {e}")
            raise
    
    @retry(max_attempts=2, delay=1)
    @timeout(30)
    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """获取订单详情"""
        try:
            if not self.connected:
                await self.connect()
            
            order = await asyncio.to_thread(
                self.exchange.fetch_order, 
                order_id, 
                symbol
            )
            
            return {
                'order_id': order['id'],
                'symbol': order['symbol'],
                'type': order['type'],
                'side': order['side'],
                'price': order['price'],
                'amount': order['amount'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'status': order['status'],
                'timestamp': order['timestamp'],
                'trades': order.get('trades', []),
            }
            
        except Exception as e:
            self.logger.error(f"获取订单详情失败: {e}")
            raise
    
    @retry(max_attempts=2, delay=1)
    @timeout(30)
    async def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """获取持仓信息（合约）"""
        try:
            if not self.connected:
                await self.connect()
            
            # OKX合约持仓
            positions = await asyncio.to_thread(self.exchange.fetch_positions, symbol)
            
            result = []
            for pos in positions:
                result.append({
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'contracts': pos['contracts'],
                    'entry_price': pos['entryPrice'],
                    'mark_price': pos['markPrice'],
                    'unrealized_pnl': pos['unrealizedPnl'],
                    'liquidation_price': pos['liquidationPrice'],
                    'leverage': pos['leverage'],
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取持仓失败: {e}")
            raise
    
    @retry(max_attempts=2, delay=1)
    @timeout(30)
    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """设置杠杆"""
        try:
            if not self.connected:
                await self.connect()
            
            # OKX设置杠杆需要特定参数
            params = {
                'leverage': leverage,
                'symbol': symbol,
            }
            
            result = await asyncio.to_thread(
                self.exchange.set_leverage, 
                leverage, 
                symbol
            )
            
            return {
                'symbol': symbol,
                'leverage': leverage,
                'info': result,
            }
            
        except Exception as e:
            self.logger.error(f"设置杠杆失败: {e}")
            raise
    
    @retry(max_attempts=2, delay=1)
    @timeout(30)
    async def get_fee(self, symbol: str) -> Dict[str, float]:
        """获取交易费率"""
        try:
            if not self.connected:
                await self.connect()
            
            # 加载市场信息
            markets = await asyncio.to_thread(self.exchange.load_markets)
            
            if symbol not in markets:
                raise ValueError(f"交易对 {symbol} 不存在")
            
            market = markets[symbol]
            
            return {
                'symbol': symbol,
                'maker': market.get('maker', 0),
                'taker': market.get('taker', 0),
                'precision': market.get('precision', {}),
            }
            
        except Exception as e:
            self.logger.error(f"获取费率失败: {e}")
            raise
    
    def get_exchange_name(self) -> str:
        """获取交易所名称"""
        return "OKX"
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected</parameter>
</write_to_file>