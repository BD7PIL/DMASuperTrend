# DMASuperTrend量化交易系统

🚀 基于双均线(DMA)和超级趋势(SuperTrend)的智能量化交易系统，具备自适应时间框架选择能力，实现多交易所自动化交易。

## 🎯 核心特性

### 智能策略引擎
- **双均线策略**: fast_ma=9, slow_ma=21（可自适应调整）
- **超级趋势指标**: period=10, multiplier=3
- **市场状态分类器**: 基于RandomForest的轻量级ML模型
- **时间框架优化器**: 自动选择最佳交易级别（15分钟/1小时/4小时等）

### 严格风险控制
- **动态仓位计算**: 根据资金规模自动调整杠杆
  - < 10,000U → 20倍杠杆
  - 10,000-100,000U → 10倍杠杆
  - > 100,000U → 3-5倍杠杆
- **分批止盈**: 30%仓位1.5倍止盈，30%仓位2.0倍止盈，40%移动止盈
- **硬止损**: 入场价±2%，日最大亏损5%

### 多交易所支持
- **OKX**: 优先支持，模拟账户开发
- **币安**: 可选支持
- **Bitget**: 可选支持
- **统一API接口**: 快速切换交易所

### 高性能架构
- **三级缓存**: 内存 → Redis → 数据库
- **多线程回测**: 1000个交易日<30秒（8核CPU）
- **事件驱动**: MarketEvent → SignalEvent → OrderEvent
- **异步IO**: 高并发处理

## 🏗️ 项目结构

```
DMASuperTrend/
├── main.py                 # 系统入口
├── requirements.txt        # Python依赖
├── .env.example           # 环境变量配置
├── README.md              # 项目文档
└── src/
    ├── __init__.py
    ├── core/              # 核心交易系统
    │   ├── __init__.py
    │   └── trading_system.py
    ├── config/            # 配置管理
    │   ├── __init__.py
    │   └── settings.py
    ├── exchanges/         # 交易所集成
    │   ├── __init__.py
    │   ├── exchange_factory.py
    │   └── exchange_interface.py
    ├── strategies/        # 策略引擎
    │   ├── __init__.py
    │   ├── dma_supertrend.py
    │   ├── market_classifier.py
    │   └── timeframe_optimizer.py
    ├── data/              # 数据管理
    │   ├── __init__.py
    │   ├── data_cache.py
    │   ├── data_fetcher.py
    │   └── feature_engineer.py
    ├── risk/              # 风险管理
    │   ├── __init__.py
    │   ├── risk_manager.py
    │   └── position_calculator.py
    ├── monitor/           # 监控通知
    │   ├── __init__.py
    │   ├── telegram_bot.py
    │   ├── dashboard.py
    │   └── performance_tracker.py
    └── utils/             # 工具函数
        ├── __init__.py
        ├── logger.py
        └── helpers.py
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入API密钥等配置
# OKX_API_KEY=your_key
# OKX_SECRET_KEY=your_secret
# ...
```

### 3. 启动系统

```bash
# 启动主系统
python main.py

# 启动Streamlit监控面板（可选）
streamlit run src/monitor/dashboard.py
```

### 4. Telegram机器人指令

```
/start - 启动系统
/status - 系统状态
/positions - 当前持仓
/balance - 账户余额
/buy [symbol] [amount] - 手动买入
/sell [symbol] [amount] - 手动卖出
/pause - 暂停交易
/resume - 恢复交易
/kpi - 查看关键指标
/report daily - 生成日报
/config - 查看当前配置
/set_leverage [value] - 设置杠杆
/set_risk [percent] - 设置风险比例
/shutdown - 安全关闭系统
```

## 📊 开发阶段

### Phase 1: 基础框架 ✅ 95%完成
- [x] 项目结构搭建
- [x] 交易所API封装（OKX优先）
- [x] 数据缓存系统
- [x] 基础回测引擎
- [x] 配置管理系统
- [x] 日志系统
- [x] 事件驱动架构
- [x] DMA+SuperTrend策略
- [x] 风险管理系统
- [x] 核心交易系统框架
- [x] 多线程回测引擎
- [x] 单元测试框架

### Phase 2: 策略优化与实盘准备 🚧 进行中
- [ ] 市场状态分类器的机器学习优化
- [ ] 时间框架选择器的动态调整算法
- [ ] 策略切换器的平滑过渡机制
- [ ] 订单状态管理
- [ ] 异常恢复机制
- [ ] 动态参数调整
- [ ] Telegram机器人集成
- [ ] 实时性能监控
- [ ] 交易报告系统

### Phase 3: 风控实盘
- [ ] 资金管理系统
- [ ] 实盘交易引擎
- [ ] Telegram通知

### Phase 4: 高级功能
- [ ] 多线程回测优化
- [ ] Streamlit前端界面
- [ ] 动态参数调整

### Phase 5: 测试部署
- [ ] 模拟交易测试
- [ ] 性能优化
- [ ] 部署文档

## 🔧 技术栈

- **Python 3.9+**
- **ccxt**: 交易所API封装
- **pandas**: 数据处理
- **scikit-learn**: 机器学习模型
- **redis**: 缓存系统
- **asyncio**: 异步处理
- **plotly**: 可视化
- **streamlit**: 前端界面
- **python-telegram-bot**: 通知系统

## 📈 性能指标

- **回测性能**: 1000个交易日 < 30秒
- **内存使用**: < 2GB（100个交易对）
- **缓存命中率**: > 80%
- **数据延迟**: < 500ms
- **订单执行**: < 100ms
- **系统可用性**: 99.9%
- **最大回撤**: < 20%
- **胜率**: > 45%
- **盈亏比**: > 1.5

## 🔒 安全特性

- API密钥加密存储（环境变量）
- 交易数据加密传输
- 操作日志完整记录
- 熔断机制（连续亏损3次暂停）
- 单币种最大仓位30%
- 滑点控制（最大2%）

## 🎮 用户交互

### 前端监控面板
- 实时K线图表（Plotly交互式）
- 策略参数可视化调整
- 持仓状态和盈亏统计
- 回测任务控制面板
- 系统性能监控仪表盘

### Telegram通知
- 实时开仓/平仓/止损通知
- 日报/周报/月报定时推送
- 远程控制系统状态

## 📝 配置说明

### 交易所配置
```python
# config/settings.py
EXCHANGE_CONFIG = {
    'okx': {
        'api_key': os.getenv('OKX_API_KEY'),
        'secret_key': os.getenv('OKX_SECRET_KEY'),
        'passphrase': os.getenv('OKX_PASSPHRASE'),
        'simulation': True,  # 模拟交易模式
    }
}
```

### 策略参数
```python
STRATEGY_CONFIG = {
    'fast_ma': 9,
    'slow_ma': 21,
    'supertrend_period': 10,
    'supertrend_multiplier': 3.0,
}
```

### 风险管理
```python
RISK_CONFIG = {
    'max_position_size': 0.3,  # 30%
    'stop_loss_percent': 2.0,
    'take_profit_percent': 5.0,
    'daily_loss_limit': 5.0,
}
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目地址: https://github.com/yourusername/DMASuperTrend
- 问题反馈: 通过GitHub Issues

---

**免责声明**: 本系统仅供学习和研究使用。量化交易存在风险，请在充分理解的基础上使用，并自行承担相关风险。