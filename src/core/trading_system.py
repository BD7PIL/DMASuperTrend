"""
主交易系统
协调所有模块，实现完整的交易流程
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from src.core.events import (
    EventManager, MarketEvent, SignalEvent, OrderEvent, 
    TradeEvent, PositionEvent, RiskEvent, SystemEvent, EventType
)
from src.config.settings import SystemConfig
from src.data.data_fetcher import DataFetcher
from src.data.data_cache import DataCache
from src.strategies.dma_supertrend import DMASuperTrendStrategy, MarketClassifier, TimeframeOptimizer
from src.risk.risk_manager import RiskManager, RiskConfig, OrderValidator
from src.exchanges.exchange_factory import ExchangeFactory
from src.utils.logger import get_trading_logger


class StrategyEngine:
    """策略执行引擎"""
    
    def __init__(self, event_manager: EventManager, config: SystemConfig):
        self.event_manager = event_manager
        self.config = config
        
        # 初始化策略组件
        self.strategy = DMASuperTrendStrategy()
        self.market_classifier = MarketClassifier()
        self.timeframe_optimizer = TimeframeOptimizer()
        
        # 策略状态
        self.current_timeframe = config.strategy.timeframe
        self.current_market_state = "trend"
        
        self.logger = logger.bind(module="StrategyEngine")
    
    async def process_market_data(self, event: MarketEvent):
        """处理市场数据，生成策略信号"""
        try:
            # 1. 分类市场状态
            df = event.data['candles']
            if len(df) >= 20:
                self.current_market_state = self.market_classifier.classify(df)
            
            # 2. 优化时间框架（基于市场状态）
            if self.current_market_state == "range":
                # 横盘市场，可能需要调整时间框架
                self.current_timeframe = self.timeframe_optimizer.recommend_timeframe(
                    symbol=event.data['symbol'],
                    volatility=0.02,  # 需要从数据计算
                    capital=10000,  # 需要从配置获取
                    frequency='medium'
                )
            
            # 3. 生成策略信号
            current_price = event.data['candles']['close'].iloc[-1]
            signal, confidence, metadata = self.strategy.generate_signal(
                event.data['candles'], 
                current_price
            )
            
            if signal != "hold":
                # 4. 发布信号事件
                signal_event = SignalEvent(
                    symbol=event.data['symbol'],
                    signal_type=signal,
                    price=current_price,
                    confidence=confidence,
                    metadata={
                        **metadata,
                        'market_state': self.current_market_state,
                        'timeframe': self.current_timeframe,
                        'source': 'strategy_engine'
                    }
                )
                self.event_manager.publish(signal_event)
                
                self.logger.info(
                    f"生成信号: {signal} {event.data['symbol']} "
                    f"置信度: {confidence:.2f} "
                    f"市场状态: {self.current_market_state}"
                )
            
        except Exception as e:
            self.logger.error(f"策略处理失败: {e}")


class TradingSystem:
    """主交易系统"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.event_manager = EventManager()
        
        # 初始化核心组件
        self.data_fetcher = DataFetcher(config, self.event_manager)
        self.data_cache = DataCache(config)
        self.strategy_engine = StrategyEngine(self.event_manager, config)
        
        # 风控组件
        risk_config = RiskConfig(
            max_leverage=config.risk.max_leverage,
            min_leverage=config.risk.min_leverage,
            max_position_size=config.risk.max_position_size,
            risk_per_trade=config.risk.risk_per_trade,
            stop_loss_percent=config.risk.stop_loss_percent,
            take_profit_1=config.risk.take_profit_1,
            take_profit_2=config.risk.take_profit_2,
            trailing_stop=config.risk.trailing_stop,
            max_consecutive_losses=config.risk.max_consecutive_losses,
            max_daily_loss=config.risk.max_daily_loss,
            min_order_size=config.risk.min_order_size
        )
        self.risk_manager = RiskManager(risk_config, self.event_manager)
        self.order_validator = OrderValidator(risk_config)
        
        # 交易所组件
        self.exchange = None
        
        # 系统状态
        self.is_running = False
        self.is_paused = False
        self.start_time = None
        
        # 订阅事件
        self._subscribe_events()
        
        self.logger = logger.bind(module="TradingSystem")
    
    def _subscribe_events(self):
        """订阅事件"""
        # 策略引擎订阅市场数据
        self.event_manager.subscribe(EventType.MARKET_DATA, self.strategy_engine.process_market_data)
        
        # 风险管理器订阅信号
        self.event_manager.subscribe(EventType.SIGNAL, self._process_signal)
        
        # 交易系统订阅订单事件
        self.event_manager.subscribe(EventType.ORDER, self._process_order)
        
        # 监控持仓变化
        self.event_manager.subscribe(EventType.POSITION, self._process_position)
        
        # 处理风控事件
        self.event_manager.subscribe(EventType.RISK, self._process_risk_event)
    
    async def initialize(self):
        """初始化交易系统"""
        try:
            self.logger.info("开始初始化交易系统...")
            
            # 1. 初始化数据缓存
            await self.data_cache.initialize()
            self.logger.info("数据缓存初始化完成")
            
            # 2. 初始化数据获取器
            if not await self.data_fetcher.initialize():
                raise Exception("数据获取器初始化失败")
            self.logger.info("数据获取器初始化完成")
            
            # 3. 初始化交易所
            exchange_config = self.config.exchange
            self.exchange = ExchangeFactory.create(
                exchange_config.name,
                api_key=exchange_config.api_key,
                secret=exchange_config.secret,
                password=exchange_config.password,
                sandbox=exchange_config.sandbox
            )
            await self.exchange.connect()
            self.logger.info(f"交易所 {exchange_config.name} 连接成功")
            
            # 4. 启动事件处理
            await self.event_manager.start()
            self.logger.info("事件管理器启动完成")
            
            self.logger.info("交易系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False
    
    async def start(self):
        """启动交易系统"""
        if self.is_running:
            self.logger.warning("系统已在运行")
            return
        
        if not await self.initialize():
            self.logger.error("初始化失败，无法启动系统")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # 发布系统启动事件
        system_event = SystemEvent(
            system_type="start",
            message="交易系统启动",
            details={
                'start_time': self.start_time.isoformat(),
                'config': {
                    'symbol': self.config.strategy.symbol,
                    'timeframe': self.config.strategy.timeframe,
                    'exchange': self.config.exchange.name
                }
            }
        )
        self.event_manager.publish(system_event)
        
        self.logger.info(f"交易系统启动成功 - 交易对: {self.config.strategy.symbol}")
        
        # 开始主循环
        await self._main_loop()
    
    async def _main_loop(self):
        """主循环"""
        symbol = self.config.strategy.symbol
        timeframe = self.config.strategy.timeframe
        
        while self.is_running:
            try:
                if self.is_paused:
                    await asyncio.sleep(1)
                    continue
                
                # 1. 获取市场数据
                candles = await self.data_fetcher.fetch_candles(symbol, timeframe, limit=100)
                
                if candles:
                    # 2. 缓存数据
                    df = await self.data_cache.get_market_data(symbol, timeframe)
                    if df is None:
                        df = candles
                        await self.data_cache.set_market_data(symbol, timeframe, df)
                    
                    # 3. 发布市场事件
                    market_event = MarketEvent(
                        symbol=symbol,
                        timeframe=timeframe,
                        candles=candles
                    )
                    self.event_manager.publish(market_event)
                
                # 4. 检查持仓和止盈止损
                await self._check_positions()
                
                # 5. 等待下一次循环
                await asyncio.sleep(self.config.system.loop_interval)
                
            except Exception as e:
                self.logger.error(f"主循环异常: {e}")
                await asyncio.sleep(5)  # 异常时等待更长时间
    
    async def _process_signal(self, event: SignalEvent):
        """处理策略信号"""
        if self.is_paused:
            return
        
        # 1. 检查信号置信度
        if event.confidence < 0.6:
            self.logger.debug(f"信号置信度过低: {event.confidence}")
            return
        
        # 2. 获取账户余额
        try:
            balance_info = await self.exchange.get_balance()
            balance = balance_info.get('USDT', {}).get('free', 0)
            
            if balance < self.config.risk.min_order_size:
                self.logger.warning(f"余额不足: {balance}U")
                return
        except Exception as e:
            self.logger.error(f"获取余额失败: {e}")
            return
        
        # 3. 风控检查
        order_request = {
            'symbol': event.symbol,
            'side': event.signal_type,
            'price': event.price,
            'amount': 0,  # 将由风控计算
            'type': 'market'
        }
        
        risk_check = self.risk_manager.check_order(order_request, balance)
        
        if not risk_check['valid']:
            self.logger.warning(f"风控拒绝: {risk_check['reason']}")
            return
        
        # 4. 调整订单
        adjusted_order = risk_check['order_request']
        
        # 5. 验证订单
        validation = self.order_validator.validate_market_order(
            adjusted_order['symbol'],
            adjusted_order['side'],
            adjusted_order['amount'],
            adjusted_order['price'],
            balance
        )
        
        if not validation['valid']:
            self.logger.warning(f"订单验证失败: {validation['reason']}")
            return
        
        # 6. 发布订单事件
        order_event = OrderEvent(
            symbol=adjusted_order['symbol'],
            order_id=f"ORD_{datetime.now().timestamp()}",
            side=adjusted_order['side'],
            order_type=adjusted_order['type'],
            price=adjusted_order['price'],
            amount=adjusted_order['amount'],
            status='pending'
        )
        self.event_manager.publish(order_event)
        
        self.logger.info(
            f"准备下单: {adjusted_order['side']} {adjusted_order['symbol']} "
            f"数量: {adjusted_order['amount']:.6f} "
            f"杠杆: {risk_check['position_info']['leverage']}x"
        )
    
    async def _process_order(self, event: OrderEvent):
        """处理订单事件"""
        if event.status != 'pending':
            return
        
        try:
            # 执行订单
            if event.side == 'buy':
                order_result = await self.exchange.create_order(
                    symbol=event.symbol,
                    side='buy',
                    order_type='market',
                    amount=event.amount
                )
            else:
                order_result = await self.exchange.create_order(
                    symbol=event.symbol,
                    side='sell',
                    order_type='market',
                    amount=event.amount
                )
            
            # 更新订单状态
            event.status = 'filled'
            
            # 发布交易事件
            trade_event = TradeEvent(
                symbol=event.symbol,
                order_id=event.order_id,
                side=event.side,
                price=event.price,
                amount=event.amount,
                fee=0.001,  # 假设手续费0.1%
                pnl=0.0  # 暂时设为0，平仓时计算
            )
            self.event_manager.publish(trade_event)
            
            # 更新持仓
            position_type = 'long' if event.side == 'buy' else 'short'
            self.risk_manager.update_position(
                event.symbol,
                position_type,
                event.amount,
                event.price,
                event.price
            )
            
            self.logger.info(f"订单执行成功: {event.symbol} {event.side} {event.amount}")
            
        except Exception as e:
            event.status = 'rejected'
            self.logger.error(f"订单执行失败: {e}")
            
            # 发布失败的订单事件
            failed_order = OrderEvent(
                symbol=event.symbol,
                order_id=event.order_id,
                side=event.side,
                order_type=event.order_type,
                price=event.price,
                amount=event.amount,
                status='rejected'
            )
            self.event_manager.publish(failed_order)
    
    async def _check_positions(self):
        """检查持仓和止盈止损"""
        if not self.risk_manager.open_positions:
            return
        
        try:
            # 获取最新价格
            ticker = await self.exchange.get_ticker(self.config.strategy.symbol)
            current_price = ticker['last']
            
            # 检查每个持仓
            for symbol in list(self.risk_manager.open_positions.keys()):
                # 检查止损
                stop_loss = self.risk_manager.check_stop_loss(symbol, current_price)
                if stop_loss:
                    await self._close_position(stop_loss)
                    continue
                
                # 检查止盈
                take_profit = self.risk_manager.check_take_profit(symbol, current_price)
                if take_profit:
                    await self._close_position(take_profit)
                    
        except Exception as e:
            self.logger.error(f"检查持仓失败: {e}")
    
    async def _close_position(self, close_signal: Dict[str, Any]):
        """平仓"""
        try:
            symbol = close_signal['symbol']
            price = close_signal['price']
            
            if close_signal['action'] == 'partial_close':
                amount = close_signal['amount']
            else:
                # 全平
                position = self.risk_manager.open_positions[symbol]
                amount = position['size']
            
            # 执行平仓
            side = 'sell' if self.risk_manager.open_positions[symbol]['type'] == 'long' else 'buy'
            
            order_result = await self.exchange.create_order(
                symbol=symbol,
                side=side,
                order_type='market',
                amount=amount
            )
            
            # 更新持仓
            if close_signal['action'] == 'partial_close':
                self.risk_manager.update_position(
                    symbol,
                    self.risk_manager.open_positions[symbol]['type'],
                    self.risk_manager.open_positions[symbol]['size'] - amount,
                    self.risk_manager.open_positions[symbol]['entry_price'],
                    price
                )
            else:
                self.risk_manager.update_position(symbol, 'flat', 0, 0, 0)
            
            # 记录交易
            pnl = 0  # 需要实际计算
            self.risk_manager.record_trade(symbol, side, price, amount, pnl)
            
            self.logger.info(f"平仓成功: {symbol} {side} {amount} 价格: {price}")
            
        except Exception as e:
            self.logger.error(f"平仓失败: {e}")
    
    def _process_position(self, event: PositionEvent):
        """处理持仓事件"""
        self.logger.info(
            f"持仓更新: {event.symbol} {event.position_type} "
            f"数量: {event.size} 未实现盈亏: {event.unrealized_pnl:.2f}"
        )
    
    def _process_risk_event(self, event: RiskEvent):
        """处理风控事件"""
        if event.level == "critical":
            self.logger.error(f"[风控] {event.message}")
            # 触发熔断时暂停交易
            if event.risk_type == "breach":
                self.pause()
        elif event.level == "warning":
            self.logger.warning(f"[风控] {event.message}")
        else:
            self.logger.info(f"[风控] {event.message}")
    
    def pause(self):
        """暂停交易"""
        self.is_paused = True
        self.logger.warning("交易已暂停")
        
        # 发布暂停事件
        event = SystemEvent(
            system_type="pause",
            message="交易暂停",
            details={'timestamp': datetime.now().isoformat()}
        )
        self.event_manager.publish(event)
    
    def resume(self):
        """恢复交易"""
        self.is_paused = False
        self.logger.info("交易已恢复")
        
        # 发布恢复事件
        event = SystemEvent(
            system_type="resume",
            message="交易恢复",
            details={'timestamp': datetime.now().isoformat()}
        )
        self.event_manager.publish(event)
    
    async def stop(self):
        """停止系统"""
        self.is_running = False
        self.is_paused = False
        
        # 关闭连接
        if self.exchange:
            await self.exchange.disconnect()
        
        # 停止事件管理器
        await self.event_manager.stop()
        
        # 停止数据获取器
        await self.data_fetcher.close()
        
        # 发布停止事件
        event = SystemEvent(
            system_type="stop",
            message="交易系统停止",
            details={
                'stop_time': datetime.now().isoformat(),
                'running_time': str(datetime.now() - self.start_time) if self.start_time else 'N/A'
            }
        )
        self.event_manager.publish(event)
        
        self.logger.info("交易系统已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'running_time': str(datetime.now() - self.start_time) if self.start_time else None,
            'symbol': self.config.strategy.symbol,
            'timeframe': self.config.strategy.timeframe,
            'market_state': self.strategy_engine.current_market_state,
            'open_positions': len(self.risk_manager.open_positions),
            'risk_status': self.risk_manager.get_risk_status(),
            'cache_stats': self.data_cache.get_stats()
        }