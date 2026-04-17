#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/15 16:00:48
Version: 1.0.0
Description: 123Bot 模块入口 (支持 python -m src 执行)
"""

import sys
import os
from config import Config, get_config, get_database, get_logger
from bot import Bot


logger = get_logger(__name__)


def main():
    """程序主入口函数"""
    logger.info("=" * 50)
    logger.info("123Bot 启动")
    logger.info("=" * 50)

    try:
        # 设置媒体路径环境变量
        if not os.getenv("MEDIA_PATH"):
            os.environ["MEDIA_PATH"] = os.path.join("/app/media")

        # 获取配置
        cft: Config = get_config()
        logger.info(f"配置加载成功: {cft}")

        # 初始化数据库
        logger.info(f"数据库路径: {cft.get_db_path()}")
        get_database(cft.get_db_path())
        logger.info("数据库初始化成功")

        # 创建并启动 Bot
        bot_app = Bot(_cft_=cft)
        logger.info("Bot 实例创建成功，开始轮询...")

        # 启动 bot 轮询
        bot_app.start_polling()

    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
