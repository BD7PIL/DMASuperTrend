"""
风险管理系统
负责仓位计算、止盈止损、熔断机制等风控功能
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
from loguru import logger

from src.core.events import RiskEvent, OrderEvent, EventType


@dataclass
class RiskConfig:
    """风控配置"""
    max_leverage: int = 20
    min_leverage: int = 3
    max_position_size: float = 0.3  # 单币种最大30%
    risk_per_trade: float = 0.02  # 单笔风险2%
    stop_loss_percent: float = 0.02  # 硬止损2%
    take_profit_1: float = 1.5  # 第一批止盈1.5倍
    take_profit_2: float = 2.0  # 第二批止盈2.0倍
    trailing_stop: float = 0.03  # 移动止盈回撤3%
    max_consecutive_losses: int = 3  # 熔断机制
    max_daily_loss: float = 0.05  # 日最大亏损5%
    min_order_size: float = 10.0  # 最小订单金额(USDT)


class PositionCalculator:
    """仓位计算器"""
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.logger = logger.bind(module="PositionCalculator")
    
    def calculate_position_size(self, balance: float, price: float, 
                               symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """
        计算仓位大小
        
        Args:
            balance: 账户余额
            price: 当前价格
            
        Returns:
            仓位信息
        """
        # 1. 根据资金规模确定杠杆
        if balance < 10000:
            leverage = self.config.max_leverage  # 20倍
        elif balance < 100000:
            leverage = 10  # 10倍
        else:
            leverage = 5  # 5倍
        
        # 确保杠杆在有效范围内
        leverage = max(self.config.min_leverage, min(leverage, self.config.max_leverage))
        
        # 2. 计算单笔风险金额
        risk_amount = balance * self.config.risk_per_trade
        
        # 3. 计算理论仓位大小（基于止损）
        # 如果价格下跌2%，损失risk_amount
        # 仓位价值 = risk_amount / 0.02
        position_value = risk_amount / self.config.stop_loss_percent
        
        # 4. 考虑杠杆
        position_value_with_leverage = position_value * leverage
        
        # 5. 计算数量
        amount = position_value_with_leverage / price
        
        # 6. 检查最大仓位限制
        max_position_value = balance * self.config.max_position_size * leverage
        if position_value_with_leverage > max_position_value:
            position_value_with_leverage = max_position_value
            amount = max_position_value / price
            self.logger.warning(f"仓位超过限制，调整为最大仓位")
        
        # 7. 检查最小订单金额
        min_amount = self.config.min_order_size / price
        if amount < min_amount:
            return {
                'valid': False,
                'reason': '订单金额过小',
                'min_amount': min_amount,
                'current_amount': amount
            }
        
        # 8. 计算止盈止损价格
        entry_price = price
        stop_loss_price = entry_price * (1 - self.config.stop_loss_percent)
        take_profit_1_price = entry_price * self.config.take_profit_1
        take_profit_2_price = entry_price * self.config.take_profit_2
        
        return {
            'valid': True,
            'leverage': leverage,
            'amount': amount,
            'position_value': position_value_with_leverage,
            'risk_amount': risk_amount,
            'stop_loss_price': stop_loss_price,
            'take_profit_1_price': take_profit_1_price,
            'take_profit_2_price': take_profit_2_price,
            'entry_price': entry_price
        }


class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: RiskConfig, event_manager=None):
        self.config = config
        self.event_manager = event_manager
        self.position_calculator = PositionCalculator(config)
        
        # 状态跟踪
        self.consecutive_losses = 0
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now().date()
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        
        self.logger = logger.bind(module="RiskManager")
    
    def check_order(self, order_request: Dict[str, Any], balance: float) -> Dict[str, Any]:
        """
        检查订单是否符合风控规则
        
        Args:
            order_request: 订单请求
            balance: 账户余额
            
        Returns:
            检查结果
        """
        # 重置每日亏损
        self._reset_daily_loss()
        
        # 1. 熔断检查
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            self._emit_risk_event(
                "breach",
                "critical",
                f"熔断触发：连续亏损{self.consecutive_losses}次，暂停交易",
                {"consecutive_losses": self.consecutive_losses}
            )
            return {
                'valid': False,
                'reason': '熔断触发',
                'message': '连续亏损达到上限，暂停交易'
            }
        
        # 2. 每日亏损检查
        if self.daily_loss >= self.config.max_daily_loss * balance:
            self._emit_risk_event(
                "breach",
                "critical",
                f"每日亏损限制：已亏损{self.daily_loss:.2f}U，上限{self.config.max_daily_loss * balance:.2f}U",
                {"daily_loss": self.daily_loss, "max_daily_loss": self.config.max_daily_loss * balance}
            )
            return {
                'valid': False,
                'reason': '每日亏损超限',
                'message': f'今日已亏损{self.daily_loss:.2f}U，达到日亏损上限'
            }
        
        # 3. 仓位计算
        price = order_request['price']
        position_info = self.position_calculator.calculate_position_size(balance, price)
        
        if not position_info['valid']:
            return position_info
        
        # 4. 检查是否超过单币种仓位限制
        symbol = order_request['symbol']
        if symbol in self.open_positions:
            existing_position = self.open_positions[symbol]
            total_value = existing_position['position_value'] + position_info['position_value']
            
            if total_value > balance * self.config.max_position_size * position_info['leverage']:
                self._emit_risk_event(
                    "breach",
                    "warning",
                    f"仓位限制：{symbol}总仓位超过{self.config.max_position_size * 100}%",
                    {"symbol": symbol, "total_value": total_value}
                )
                return {
                    'valid': False,
                    'reason': '仓位超限',
                    'message': f'{symbol}总仓位超过限制'
                }
        
        # 5. 调整订单数量为风控计算的值
        order_request['amount'] = position_info['amount']
        order_request['leverage'] = position_info['leverage']
        
        return {
            'valid': True,
            'position_info': position_info,
            'order_request': order_request
        }
    
    def update_position(self, symbol: str, position_type: str, size: float, 
                       entry_price: float, mark_price: float):
        """更新持仓信息"""
        if size == 0:
            # 平仓
            if symbol in self.open_positions:
                self.open_positions.pop(symbol)
        else:
            # 开仓或更新
            self.open_positions[symbol] = {
                'type': position_type,
                'size': size,
                'entry_price': entry_price,
                'mark_price': mark_price,
                'unrealized_pnl': (mark_price - entry_price) * size if position_type == 'long' else (entry_price - mark_price) * size,
                'updated_at': datetime.now()
            }
    
    def check_stop_loss(self, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
        """检查止损"""
        if symbol not in self.open_positions:
            return None
        
        position = self.open_positions[symbol]
        entry_price = position['entry_price']
        position_type = position['type']
        
        # 计算当前盈亏
        if position_type == 'long':
            pnl = (current_price - entry_price) / entry_price
        else:
            pnl = (entry_price - current_price) / entry_price
        
        # 硬止损
        if pnl <= -self.config.stop_loss_percent:
            self._emit_risk_event(
                "stop_loss",
                "critical",
                f"触发硬止损: {symbol} 当前价格 {current_price}, 入场价 {entry_price}",
                {
                    'symbol': symbol,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'pnl': pnl
                }
            )
            return {
                'action': 'close',
                'reason': 'stop_loss',
                'symbol': symbol,
                'price': current_price
            }
        
        return None
    
    def check_take_profit(self, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
        """检查止盈"""
        if symbol not in self.open_positions:
            return None
        
        position = self.open_positions[symbol]
        entry_price = position['entry_price']
        position_type = position['type']
        size = position['size']
        
        # 计算当前盈亏倍数
        if position_type == 'long':
            pnl_multiple = (current_price - entry_price) / (entry_price * self.config.stop_loss_percent)
        else:
            pnl_multiple = (entry_price - current_price) / (entry_price * self.config.stop_loss_percent)
        
        # 第一批止盈 (1.5倍)
        if pnl_multiple >= self.config.take_profit_1 and pnl_multiple < self.config.take_profit_2:
            close_amount = size * 0.3  # 平仓30%
            self._emit_risk_event(
                "take_profit",
                "info",
                f"第一止盈: {symbol} 平仓30%",
                {
                    'symbol': symbol,
                    'current_price': current_price,
                    'close_amount': close_amount,
                    'pnl_multiple': pnl_multiple
                }
            )
            return {
                'action': 'partial_close',
                'reason': 'take_profit_1',
                'symbol': symbol,
                'amount': close_amount,
                'price': current_price
            }
        
        # 第二批止盈 (2倍)
        elif pnl_multiple >= self.config.take_profit_2:
            close_amount = size * 0.3  # 再平仓30%
            self._emit_risk_event(
                "take_profit",
                "info",
                f"第二止盈: {symbol} 平仓30%",
                {
                    'symbol': symbol,
                    'current_price': current_price,
                    'close_amount': close_amount,
                    'pnl_multiple': pnl_multiple
                }
            )
            return {
                'action': 'partial_close',
                'reason': 'take_profit_2',
                'symbol': symbol,
                'amount': close_amount,
                'price': current_price
            }
        
        # 移动止盈 (剩余40%)
        elif pnl_multiple > self.config.take_profit_2:
            # 检查是否从高点回撤
            highest_price = position.get('highest_price', current_price)
            if current_price > highest_price:
                position['highest_price'] = current_price
                return None
            
            # 回撤超过3%则平仓
            if (highest_price - current_price) / highest_price >= self.config.trailing_stop:
                close_amount = size * 0.4  # 平仓剩余40%
                self._emit_risk_event(
                    "take_profit",
                    "info",
                    f"移动止盈: {symbol} 回撤触发，平仓40%",
                    {
                        'symbol': symbol,
                        'current_price': current_price,
                        'highest_price': highest_price,
                        'close_amount': close_amount
                    }
                )
                return {
                    'action': 'close',
                    'reason': 'trailing_stop',
                    'symbol': symbol,
                    'price': current_price
                }
        
        return None
    
    def record_trade(self, symbol: str, side: str, price: float, amount: float, 
                    pnl: float = 0.0, fee: float = 0.0):
        """记录交易"""
        trade = {
            'symbol': symbol,
            'side': side,
            'price': price,
            'amount': amount,
            'pnl': pnl,
            'fee': fee,
            'timestamp': datetime.now()
        }
        self.trade_history.append(trade)
        
        # 更新亏损统计
        if pnl < 0:
            self.daily_loss += abs(pnl)
            self.consecutive_losses += 1
        elif pnl > 0:
            self.consecutive_losses = 0
        
        # 保留最近100笔交易
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
    
    def _reset_daily_loss(self):
        """重置每日亏损"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_loss = 0.0
            self.last_reset_date = today
            self.logger.info("重置每日亏损统计")
    
    def _emit_risk_event(self, risk_type: str, level: str, message: str, details: Dict[str, Any]):
        """发布风控事件"""
        if self.event_manager:
            event = RiskEvent(
                risk_type=risk_type,
                level=level,
                message=message,
                details=details
            )
            self.event_manager.publish(event)
        
        # 记录日志
        if level == "critical":
            self.logger.error(f"[风控] {message}")
        elif level == "warning":
            self.logger.warning(f"[风控] {message}")
        else:
            self.logger.info(f"[风控] {message}")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """获取风控状态"""
        return {
            'consecutive_losses': self.consecutive_losses,
            'daily_loss': self.daily_loss,
            'open_positions': len(self.open_positions),
            'total_trades': len(self.trade_history),
            'is_trading_paused': self.consecutive_losses >= self.config.max_consecutive_losses,
            'last_reset_date': self.last_reset_date.isoformat()
        }


class OrderValidator:
    """订单验证器"""
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.logger = logger.bind(module="OrderValidator")
    
    def validate_market_order(self, symbol: str, side: str, amount: float, 
                             price: float, balance: float) -> Dict[str, Any]:
        """验证市价单"""
        # 检查最小订单金额
        order_value = amount * price
        if order_value < self.config.min_order_size:
            return {
                'valid': False,
                'reason': '订单金额过小',
                'min_value': self.config.min_order_size,
                'current_value': order_value
            }
        
        # 检查是否超过可用余额
        if order_value > balance:
            return {
                'valid': False,
                'reason': '余额不足',
                'available': balance,
                'required': order_value
            }
        
        # 检查数量精度
        if amount <= 0:
            return {
                'valid': False,
                'reason': '数量必须大于0'
            }
        
        return {'valid': True}
    
    def validate_limit_order(self, symbol: str, side: str, amount: float, 
                            price: float, balance: float) -> Dict[str, Any]:
        """验证限价单"""
        # 基础验证
        result = self.validate_market_order(symbol, side, amount, price, balance)
        if not result['valid']:
            return result
        
        # 检查价格合理性
        if price <= 0:
            return {
                'valid': False,
                'reason': '价格必须大于0'
            }
        
        return {'valid': True}
    
    def validate_leverage(self, leverage: int, symbol: str) -> Dict[str, Any]:
        """验证杠杆"""
        if leverage < self.config.min_leverage:
            return {
                'valid': False,
                'reason': '杠杆过低',
                'min_leverage': self.config.min_leverage,
                'current_leverage': leverage
            }
        
        if leverage > self.config.max_leverage:
            return {
                'valid': False,
                'reason': '杠杆过高',
                'max_leverage': self.config.max_leverage,
                'current_leverage': leverage
            }
        
        return {'valid': True}