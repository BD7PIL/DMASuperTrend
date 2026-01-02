#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMASuperTrend量化交易系统主入口
"""

import asyncio
import logging
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.trading_system import TradingSystem
from src.config.settings import load_config
from src.utils.logger import setup_logger

async def main():
    """主函数"""
    # 设置日志
    setup_logger()
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置
        config = load_config()
        logger.info("配置加载成功")
        
        # 初始化交易系统
        trading_system = TradingSystem(config)
        
        # 启动系统
        logger.info("启动DMASuperTrend交易系统...")
        await trading_system.start()
        
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())