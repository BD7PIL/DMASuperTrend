# 系统架构设计

## 整体架构
```
DMASuperTrend量化交易系统
├── 核心层 (Core)
│   ├── TradingSystem - 主交易引擎
│   ├── EventManager - 事件驱动管理
│   └── StrategyEngine - 策略执行引擎
├── 数据层 (Data)
│   ├── DataFetcher - 数据获取
│   ├── DataCache - 三级缓存系统
│   └── FeatureEngineer - 特征工程
├── 策略层 (Strategies)
│   ├── DMASuperTrendStrategy - 双均线+超级趋势
│   ├── MarketClassifier - 市场状态分类器
│   └── TimeframeOptimizer - 时间框架优化器
├── 交易层 (Exchanges)
│   ├── ExchangeFactory - 交易所工厂
│   ├── ExchangeInterface - 统一接口
│   └── OKXAdapter - OKX适配器
├── 风控层 (Risk)
│   ├── RiskManager - 风险管理器
│   └── PositionCalculator - 仓位计算
└── 监控层 (Monitor)
    ├── TelegramBot - Telegram通知
    ├── Dashboard - 监控面板
    └── PerformanceTracker - 性能追踪
```

## 事件驱动架构
```
MarketEvent → DataCache → FeatureEngineer → MarketClassifier
                                           ↓
                                   TimeframeOptimizer
                                           ↓
                                   DMASuperTrendStrategy
                                           ↓
                                   RiskManager
                                           ↓
                                   OrderEvent → Exchange
```

## 数据流设计
1. **实时数据流**: Exchange → DataFetcher → DataCache → Strategy
2. **回测数据流**: HistoricalDB → DataCache → BacktestEngine → Strategy
3. **缓存层级**: Memory → Redis → Database

## 关键技术决策
- **异步IO**: asyncio处理所有网络请求
- **多线程回测**: concurrent.futures并行计算
- **事件驱动**: 解耦数据、策略、执行
- **模块化设计**: 易于扩展和维护