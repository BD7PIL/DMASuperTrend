# 技术栈和开发环境

## 核心技术栈
- **Python**: 3.9+
- **交易所API**: ccxt
- **数据处理**: pandas, numpy
- **机器学习**: scikit-learn
- **缓存**: redis
- **异步处理**: asyncio
- **可视化**: plotly, streamlit
- **通知**: python-telegram-bot

## 开发环境
- **操作系统**: Windows/Linux/Mac
- **虚拟环境**: venv
- **包管理**: pip
- **版本控制**: Git + GitHub
- **IDE**: VSCode

## 依赖管理
```
ccxt>=4.3.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
redis>=5.0.0
python-dotenv>=1.0.0
ta-lib>=0.4.25
pandas-ta>=0.3.14
asyncio>=3.4.3
aiohttp>=3.8.0
joblib>=1.3.0
requests>=2.31.0
python-telegram-bot>=20.0.0
plotly>=5.15.0
streamlit>=1.28.0
matplotlib>=3.7.0
loguru>=0.7.0
pyyaml>=6.0.0
pytest>=7.4.0
psutil>=5.9.0
```

## Windows适配要点
- **路径处理**: 使用pathlib跨平台兼容
- **命令行**: PowerShell替代bash
- **服务管理**: Redis, PostgreSQL
- **虚拟环境**: Scripts\activate

## 技术约束
- **内存限制**: < 2GB (100个交易对)
- **响应时间**: < 1秒 (前端)
- **数据延迟**: < 500ms
- **订单执行**: < 100ms

## 工具使用模式
- **Memory Bank**: 存储项目架构和决策
- **File System**: 管理项目文件结构
- **Context7**: 处理复杂代码逻辑
- **GitHub**: 版本控制和协作
- **Fetch**: 获取市场数据和文档