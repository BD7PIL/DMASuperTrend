"""
DMA + SuperTrend 策略
双均线 + 超级趋势组合策略
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from src.core.events import SignalEvent


@dataclass
class StrategyConfig:
    """策略配置"""
    fast_ma: int = 9
    slow_ma: int = 21
    super_trend_period: int = 10
    super_trend_multiplier: float = 3.0
    min_confidence: float = 0.6


class SuperTrendIndicator:
    """超级趋势指标计算"""
    
    def __init__(self, period: int = 10, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算超级趋势指标
        
        Args:
            df: 包含high, low, close的DataFrame
            
        Returns:
            DataFrame包含SuperTrend值和方向
        """
        # 计算ATR (平均真实波动范围)
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 真实波动范围
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR
        atr = tr.rolling(window=self.period).mean()
        
        # 中轨
        hl2 = (high + low) / 2
        upper_band = hl2 + self.multiplier * atr
        lower_band = hl2 - self.multiplier * atr
        
        # 超级趋势计算
        super_trend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        for i in range(len(df)):
            if i == 0:
                super_trend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
                continue
                
            # 上一期的值
            prev_st = super_trend.iloc[i-1]
            prev_dir = direction.iloc[i-1]
            
            # 当前值
            curr_lower = lower_band.iloc[i]
            curr_upper = upper_band.iloc[i]
            curr_close = close.iloc[i]
            prev_close = close.iloc[i-1]
            
            if prev_dir == 1:  # 上升趋势
                if curr_lower > prev_st:
                    super_trend.iloc[i] = curr_lower
                else:
                    super_trend.iloc[i] = prev_st
                
                if curr_close < super_trend.iloc[i]:
                    direction.iloc[i] = -1
                    super_trend.iloc[i] = curr_upper
                else:
                    direction.iloc[i] = 1
            else:  # 下降趋势
                if curr_upper < prev_st:
                    super_trend.iloc[i] = curr_upper
                else:
                    super_trend.iloc[i] = prev_st
                
                if curr_close > super_trend.iloc[i]:
                    direction.iloc[i] = 1
                    super_trend.iloc[i] = curr_lower
                else:
                    direction.iloc[i] = -1
        
        df['super_trend'] = super_trend
        df['super_trend_dir'] = direction
        
        return df


class DMASuperTrendStrategy:
    """DMA + SuperTrend 策略"""
    
    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()
        self.super_trend = SuperTrendIndicator(
            period=self.config.super_trend_period,
            multiplier=self.config.super_trend_multiplier
        )
        self.logger = logger.bind(module="DMASuperTrendStrategy")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            df: K线数据
            
        Returns:
            包含指标的DataFrame
        """
        # 计算双均线
        df['fast_ma'] = df['close'].rolling(window=self.config.fast_ma).mean()
        df['slow_ma'] = df['close'].rolling(window=self.config.slow_ma).mean()
        
        # 计算SuperTrend
        df = self.super_trend.calculate(df)
        
        # 计算金叉/死叉
        df['ma_cross'] = 0
        df.loc[df['fast_ma'] > df['slow_ma'], 'ma_cross'] = 1
        df.loc[df['fast_ma'] < df['slow_ma'], 'ma_cross'] = -1
        
        # 计算趋势强度
        df['trend_strength'] = abs(df['fast_ma'] - df['slow_ma']) / df['slow_ma']
        
        # 计算RSI (14周期)
        df['rsi'] = self._calculate_rsi(df['close'], period=14)
        
        # 计算波动率
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signal(self, df: pd.DataFrame, current_price: float) -> Tuple[str, float, Dict[str, Any]]:
        """
        生成交易信号
        
        Args:
            df: 历史数据
            current_price: 当前价格
            
        Returns:
            (信号类型, 置信度, 元数据)
        """
        if len(df) < max(self.config.fast_ma, self.config.slow_ma, self.config.super_trend_period):
            return "hold", 0.0, {}
        
        # 计算指标
        df_with_indicators = self.calculate_indicators(df.copy())
        latest = df_with_indicators.iloc[-1]
        
        # 信号逻辑
        signal = "hold"
        confidence = 0.0
        metadata = {}
        
        # 1. 双均线金叉 + SuperTrend看涨
        if (latest['ma_cross'] == 1 and  # 均线金叉
            latest['super_trend_dir'] == 1 and  # SuperTrend看涨
            current_price > latest['super_trend']):  # 价格在SuperTrend上方
            
            signal = "buy"
            confidence = self._calculate_buy_confidence(df_with_indicators, latest, current_price)
            metadata = {
                'fast_ma': latest['fast_ma'],
                'slow_ma': latest['slow_ma'],
                'super_trend': latest['super_trend'],
                'trend_strength': latest['trend_strength'],
                'rsi': latest['rsi'],
                'volatility': latest['volatility']
            }
            
        # 2. 双均线死叉 + SuperTrend看跌
        elif (latest['ma_cross'] == -1 and  # 均线死叉
              latest['super_trend_dir'] == -1 and  # SuperTrend看跌
              current_price < latest['super_trend']):  # 价格在SuperTrend下方
            
            signal = "sell"
            confidence = self._calculate_sell_confidence(df_with_indicators, latest, current_price)
            metadata = {
                'fast_ma': latest['fast_ma'],
                'slow_ma': latest['slow_ma'],
                'super_trend': latest['super_trend'],
                'trend_strength': latest['trend_strength'],
                'rsi': latest['rsi'],
                'volatility': latest['volatility']
            }
        
        # 3. 横盘或不确定，保持观望
        else:
            signal = "hold"
            confidence = 0.5
            metadata = {
                'reason': 'no_clear_signal',
                'fast_ma': latest['fast_ma'],
                'slow_ma': latest['slow_ma'],
                'super_trend': latest['super_trend'],
                'trend_strength': latest['trend_strength']
            }
        
        # 如果置信度低于阈值，改为hold
        if confidence < self.config.min_confidence:
            signal = "hold"
            confidence = max(confidence, 0.5)
        
        return signal, confidence, metadata
    
    def _calculate_buy_confidence(self, df: pd.DataFrame, latest: pd.Series, current_price: float) -> float:
        """计算买入置信度"""
        confidence = 0.6  # 基础置信度
        
        # 1. 趋势强度
        trend_strength = latest['trend_strength']
        if trend_strength > 0.02:  # 趋势较强
            confidence += 0.15
        elif trend_strength > 0.01:
            confidence += 0.08
        
        # 2. RSI条件 (不超买)
        rsi = latest['rsi']
        if 30 < rsi < 70:  # 理想范围
            confidence += 0.1
        elif rsi <= 30:  # 超卖，可能反弹
            confidence += 0.15
        elif rsi >= 70:  # 超买，风险
            confidence -= 0.1
        
        # 3. 价格与SuperTrend的距离
        st_distance = (current_price - latest['super_trend']) / latest['super_trend']
        if st_distance > 0.01:  # 价格明显高于SuperTrend
            confidence += 0.05
        
        # 4. 波动率适中
        volatility = latest['volatility']
        if 0.01 < volatility < 0.05:  # 适中波动
            confidence += 0.05
        elif volatility > 0.08:  # 波动过大
            confidence -= 0.1
        
        return min(confidence, 0.95)
    
    def _calculate_sell_confidence(self, df: pd.DataFrame, latest: pd.Series, current_price: float) -> float:
        """计算卖出置信度"""
        confidence = 0.6  # 基础置信度
        
        # 1. 趋势强度
        trend_strength = latest['trend_strength']
        if trend_strength > 0.02:  # 趋势较强
            confidence += 0.15
        elif trend_strength > 0.01:
            confidence += 0.08
        
        # 2. RSI条件
        rsi = latest['rsi']
        if 30 < rsi < 70:  # 理想范围
            confidence += 0.1
        elif rsi >= 70:  # 超买，可能回调
            confidence += 0.15
        elif rsi <= 30:  # 超卖，可能反弹
            confidence -= 0.1
        
        # 3. 价格与SuperTrend的距离
        st_distance = (latest['super_trend'] - current_price) / latest['super_trend']
        if st_distance > 0.01:  # 价格明显低于SuperTrend
            confidence += 0.05
        
        # 4. 波动率适中
        volatility = latest['volatility']
        if 0.01 < volatility < 0.05:  # 适中波动
            confidence += 0.05
        elif volatility > 0.08:  # 波动过大
            confidence -= 0.1
        
        return min(confidence, 0.95)
    
    def get_required_history(self) -> int:
        """获取所需历史数据长度"""
        return max(self.config.fast_ma, self.config.slow_ma, self.config.super_trend_period) + 50
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': 'DMA_SuperTrend',
            'version': '1.0',
            'parameters': {
                'fast_ma': self.config.fast_ma,
                'slow_ma': self.config.slow_ma,
                'super_trend_period': self.config.super_trend_period,
                'super_trend_multiplier': self.config.super_trend_multiplier,
                'min_confidence': self.config.min_confidence
            },
            'description': '双均线 + 超级趋势组合策略，金叉+SuperTrend看涨时买入，死叉+SuperTrend看跌时卖出'
        }


class MarketClassifier:
    """市场状态分类器"""
    
    def __init__(self):
        self.logger = logger.bind(module="MarketClassifier")
    
    def classify(self, df: pd.DataFrame) -> str:
        """
        分类市场状态
        
        Args:
            df: K线数据
            
        Returns:
            市场状态: 'trend' (趋势) 或 'range' (横盘)
        """
        if len(df) < 20:
            return "trend"  # 默认趋势
        
        # 计算指标
        returns = df['close'].pct_change().dropna()
        volatility = returns.std()
        
        # 计算ADX趋势指标
        adx = self._calculate_adx(df, period=14)
        
        # 判断标准
        # 1. 波动率阈值
        volatility_threshold = 0.02
        
        # 2. ADX阈值 (趋势强度)
        adx_threshold = 25
        
        # 如果波动率低且ADX低，则为横盘
        if volatility < volatility_threshold and adx < adx_threshold:
            return "range"
        
        # 否则为趋势
        return "trend"
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算ADX指标"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算+DM和-DM
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        # 计算真实波动范围
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算平滑后的值
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean())
        minus_di = abs(100 * (minus_dm.rolling(window=period).mean() / tr.rolling(window=period).mean()))
        
        # 计算ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean().iloc[-1]
        
        return adx if not pd.isna(adx) else 0


class TimeframeOptimizer:
    """时间框架优化器"""
    
    def __init__(self):
        self.logger = logger.bind(module="TimeframeOptimizer")
        self.timeframes = ['5m', '15m', '30m', '1h', '4h']
    
    def recommend_timeframe(self, symbol: str, volatility: float, 
                           capital: float, frequency: str = 'medium') -> str:
        """
        推荐最佳时间框架
        
        Args:
            symbol: 交易对
            volatility: 波动率
            capital: 资金规模
            frequency: 交易频率 ('low', 'medium', 'high')
            
        Returns:
            推荐的时间框架
        """
        # 基于波动率的选择
        if volatility > 0.05:  # 高波动
            base_tf = '15m'
        elif volatility > 0.02:  # 中等波动
            base_tf = '30m'
        else:  # 低波动
            base_tf = '1h'
        
        # 基于资金规模的调整
        if capital < 10000:
            leverage_factor = 1  # 小资金，更短周期
        elif capital < 100000:
            leverage_factor = 0  # 中等资金
        else:
            leverage_factor = -1  # 大资金，更长周期
        
        # 基于交易频率的调整
        freq_factor = 0
        if frequency == 'high':
            freq_factor = 1
        elif frequency == 'low':
            freq_factor = -1
        
        # 综合调整
        total_adjustment = leverage_factor + freq_factor
        
        # 应用调整
        if total_adjustment > 0:
            # 向更短周期调整
            if base_tf == '1h':
                return '30m'
            elif base_tf == '30m':
                return '15m'
            elif base_tf == '15m':
                return '5m'
        elif total_adjustment < 0:
            # 向更长周期调整
            if base_tf == '5m':
                return '15m'
            elif base_tf == '15m':
                return '30m'
            elif base_tf == '30m':
                return '1h'
        
        return base_tf
    
    def optimize_parameters(self, df: pd.DataFrame, param_ranges: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        优化策略参数
        
        Args:
            df: 历史数据
            param_ranges: 参数范围
            
        Returns:
            最优参数
        """
        # 简化的网格搜索
        best_params = None
        best_score = -float('inf')
        
        # 生成参数组合（简化版本，实际可使用贝叶斯优化）
        for fast_ma in param_ranges.get('fast_ma', [9]):
            for slow_ma in param_ranges.get('slow_ma', [21]):
                if slow_ma <= fast_ma:
                    continue
                
                for st_period in param_ranges.get('super_trend_period', [10]):
                    for st_mult in param_ranges.get('super_trend_multiplier', [3.0]):
                        # 评估参数组合
                        score = self._evaluate_params(df, fast_ma, slow_ma, st_period, st_mult)
                        
                        if score > best_score:
                            best_score = score
                            best_params = {
                                'fast_ma': fast_ma,
                                'slow_ma': slow_ma,
                                'super_trend_period': st_period,
                                'super_trend_multiplier': st_mult,
                                'score': score
                            }
        
        return best_params or {}
    
    def _evaluate_params(self, df: pd.DataFrame, fast_ma: int, slow_ma: int, 
                        st_period: int, st_mult: float) -> float:
        """评估参数组合"""
        strategy = DMASuperTrendStrategy(
            StrategyConfig(
                fast_ma=fast_ma,
                slow_ma=slow_ma,
                super_trend_period=st_period,
                super_trend_multiplier=st_mult
            )
        )
        
        # 简化回测评估
        signals = []
        for i in range(len(df) - 1):
            if i < max(fast_ma, slow_ma, st_period) + 50:
                continue
            
            subset = df.iloc[:i+1]
            signal, confidence, _ = strategy.generate_signal(subset, df.iloc[i]['close'])
            
            if signal in ['buy', 'sell']:
                signals.append((signal, confidence))
        
        if not signals:
            return 0
        
        # 计算平均置信度和信号数量
        avg_confidence = sum(s for _, s in signals) / len(signals)
        signal_count = len(signals)
        
        # 评分：高置信度 + 适度信号数量
        score = avg_confidence * 0.7 + min(signal_count / 50, 1.0) * 0.3
        
        return score