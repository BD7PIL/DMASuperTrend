"""
事件驱动架构
定义系统中的所有事件类型和事件管理器
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio
from decimal import Decimal


class EventType(Enum):
    """事件类型枚举"""
    MARKET_DATA = "market_data"  # 市场数据更新
    SIGNAL = "signal"  # 策略信号
    ORDER = "order"  # 订单事件
    TRADE = "trade"  # 交易执行
    POSITION = "position"  # 持仓更新
    RISK = "risk"  # 风控事件
    SYSTEM = "system"  # 系统事件


@dataclass
class Event:
    """基础事件类"""
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "unknown"
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class MarketEvent(Event):
    """市场数据事件"""
    symbol: str
    timeframe: str
    candles: List[Dict[str, Any]]
    
    def __init__(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]], source: str = "data_fetcher"):
        super().__init__(
            event_type=EventType.MARKET_DATA,
            timestamp=datetime.now(),
            data={
                'symbol': symbol,
                'timeframe': timeframe,
                'candles': candles
            },
            source=source
        )
        self.symbol = symbol
        self.timeframe = timeframe
        self.candles = candles


@dataclass
class SignalEvent(Event):
    """策略信号事件"""
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    price: float
    confidence: float
    metadata: Dict[str, Any] = None
    
    def __init__(self, symbol: str, signal_type: str, price: float, 
                 confidence: float, metadata: Dict[str, Any] = None, source: str = "strategy"):
        super().__init__(
            event_type=EventType.SIGNAL,
            timestamp=datetime.now(),
            data={
                'symbol': symbol,
                'signal_type': signal_type,
                'price': price,
                'confidence': confidence,
                'metadata': metadata or {}
            },
            source=source
        )
        self.symbol = symbol
        self.signal_type = signal_type
        self.price = price
        self.confidence = confidence
        self.metadata = metadata or {}


@dataclass
class OrderEvent(Event):
    """订单事件"""
    symbol: str
    order_id: str
    side: str  # 'buy', 'sell'
    order_type: str  # 'market', 'limit'
    price: float
    amount: float
    status: str  # 'pending', 'filled', 'cancelled', 'rejected'
    
    def __init__(self, symbol: str, order_id: str, side: str, order_type: str,
                 price: float, amount: float, status: str = 'pending', source: str = "risk_manager"):
        super().__init__(
            event_type=EventType.ORDER,
            timestamp=datetime.now(),
            data={
                'symbol': symbol,
                'order_id': order_id,
                'side': side,
                'order_type': order_type,
                'price': price,
                'amount': amount,
                'status': status
            },
            source=source
        )
        self.symbol = symbol
        self.order_id = order_id
        self.side = side
        self.order_type = order_type
        self.price = price
        self.amount = amount
        self.status = status


@dataclass
class TradeEvent(Event):
    """交易执行事件"""
    symbol: str
    order_id: str
    side: str
    price: float
    amount: float
    fee: float
    pnl: float = 0.0
    
    def __init__(self, symbol: str, order_id: str, side: str,
                 price: float, amount: float, fee: float, pnl: float = 0.0, source: str = "exchange"):
        super().__init__(
            event_type=EventType.TRADE,
            timestamp=datetime.now(),
            data={
                'symbol': symbol,
                'order_id': order_id,
                'side': side,
                'price': price,
                'amount': amount,
                'fee': fee,
                'pnl': pnl
            },
            source=source
        )
        self.symbol = symbol
        self.order_id = order_id
        self.side = side
        self.price = price
        self.amount = amount
        self.fee = fee
        self.pnl = pnl


@dataclass
class PositionEvent(Event):
    """持仓事件"""
    symbol: str
    position_type: str  # 'long', 'short', 'flat'
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    
    def __init__(self, symbol: str, position_type: str, size: float,
                 entry_price: float, mark_price: float, unrealized_pnl: float, source: str = "exchange"):
        super().__init__(
            event_type=EventType.POSITION,
            timestamp=datetime.now(),
            data={
                'symbol': symbol,
                'position_type': position_type,
                'size': size,
                'entry_price': entry_price,
                'mark_price': mark_price,
                'unrealized_pnl': unrealized_pnl
            },
            source=source
        )
        self.symbol = symbol
        self.position_type = position_type
        self.size = size
        self.entry_price = entry_price
        self.mark_price = mark_price
        self.unrealized_pnl = unrealized_pnl


@dataclass
class RiskEvent(Event):
    """风控事件"""
    risk_type: str  # 'stop_loss', 'take_profit', 'margin_call', 'breach'
    level: str  # 'warning', 'critical'
    message: str
    details: Dict[str, Any]
    
    def __init__(self, risk_type: str, level: str, message: str, 
                 details: Dict[str, Any] = None, source: str = "risk_manager"):
        super().__init__(
            event_type=EventType.RISK,
            timestamp=datetime.now(),
            data={
                'risk_type': risk_type,
                'level': level,
                'message': message,
                'details': details or {}
            },
            source=source
        )
        self.risk_type = risk_type
        self.level = level
        self.message = message
        self.details = details or {}


@dataclass
class SystemEvent(Event):
    """系统事件"""
    system_type: str  # 'start', 'stop', 'error', 'config_update'
    message: str
    details: Dict[str, Any] = None
    
    def __init__(self, system_type: str, message: str, 
                 details: Dict[str, Any] = None, source: str = "system"):
        super().__init__(
            event_type=EventType.SYSTEM,
            timestamp=datetime.now(),
            data={
                'system_type': system_type,
                'message': message,
                'details': details or {}
            },
            source=source
        )
        self.system_type = system_type
        self.message = message
        self.details = details or {}


class EventManager:
    """事件管理器 - 负责事件的分发和处理"""
    
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}
        self._all_listeners: List[Callable] = []
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._processing_task = None
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """订阅特定类型事件"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def subscribe_all(self, callback: Callable):
        """订阅所有事件"""
        self._all_listeners.append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """取消订阅"""
        if event_type in self._listeners:
            self._listeners[event_type] = [cb for cb in self._listeners[event_type] if cb != callback]
    
    def publish(self, event: Event):
        """发布事件到队列"""
        self._event_queue.put_nowait(event)
    
    async def emit(self, event: Event):
        """直接触发事件（同步处理）"""
        # 通知所有监听器
        for callback in self._all_listeners:
            try:
                await self._handle_callback(callback, event)
            except Exception as e:
                print(f"Error in all-listener callback: {e}")
        
        # 通知特定类型监听器
        if event.event_type in self._listeners:
            for callback in self._listeners[event.event_type]:
                try:
                    await self._handle_callback(callback, event)
                except Exception as e:
                    print(f"Error in typed-listener callback: {e}")
    
    async def _handle_callback(self, callback: Callable, event: Event):
        """处理回调，支持异步和同步函数"""
        import inspect
        if inspect.iscoroutinefunction(callback):
            await callback(event)
        else:
            callback(event)
    
    async def process_events(self):
        """处理事件队列"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self.emit(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing event: {e}")
    
    async def start(self):
        """启动事件处理"""
        if not self._running:
            self._running = True
            self._processing_task = asyncio.create_task(self.process_events())
    
    async def stop(self):
        """停止事件处理"""
        self._running = False
        if self._processing_task:
            await self._processing_task
        # 清空队列
        while not self._event_queue.empty():
            self._event_queue.get_nowait()
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self._event_queue.qsize()
    
    async def wait_for_event(self, event_type: EventType, timeout: float = 10.0) -> Optional[Event]:
        """等待特定类型事件"""
        try:
            start_time = asyncio.get_event_loop().time()
            while True:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    return None
                
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                if event.event_type == event_type:
                    return event
                else:
                    # 放回队列，继续等待
                    self._event_queue.put_nowait(event)
        except asyncio.TimeoutError:
            return None