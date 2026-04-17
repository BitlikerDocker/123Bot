#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/15 15:00:00
Version: 1.0.0
Description: 日志管理模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


# 默认日志配置
_DEFAULT_LOG_LEVEL_ = logging.INFO
_DEFAULT_LOG_FORMAT_ = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DEFAULT_LOG_DATE_FORMAT_ = "%Y-%m-%d %H:%M:%S"
_DEFAULT_LOG_MAX_BYTES_ = 10 * 1024 * 1024  # 10MB
_DEFAULT_LOG_BACKUP_COUNT_ = 5


class LoggerManager:
    """日志管理器"""

    _instance: Optional["LoggerManager"] = None
    _loggers = {}

    def __init__(self):
        self.log_dir: Optional[str] = None
        self.log_level = _DEFAULT_LOG_LEVEL_
        self.log_format = _DEFAULT_LOG_FORMAT_
        self.log_date_format = _DEFAULT_LOG_DATE_FORMAT_
        self.max_bytes = _DEFAULT_LOG_MAX_BYTES_
        self.backup_count = _DEFAULT_LOG_BACKUP_COUNT_
        self._root_handler_added = False

    @classmethod
    def get_instance(cls) -> "LoggerManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init(
        self,
        log_dir: str,
        log_level: int = _DEFAULT_LOG_LEVEL_,
        log_format: str = _DEFAULT_LOG_FORMAT_,
        log_date_format: str = _DEFAULT_LOG_DATE_FORMAT_,
        max_bytes: int = _DEFAULT_LOG_MAX_BYTES_,
        backup_count: int = _DEFAULT_LOG_BACKUP_COUNT_,
    ):
        """
        初始化日志管理器

        Args:
            log_dir: 日志文件目录
            log_level: 日志级别
            log_format: 日志格式
            log_date_format: 日期格式
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的日志文件数量
        """
        self.log_dir = log_dir
        self.log_level = log_level
        self.log_format = log_format
        self.log_date_format = log_date_format
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # 创建日志目录
        os.makedirs(self.log_dir, exist_ok=True)

        # 配置根日志器
        self._setup_root_logger()

    def _setup_root_logger(self):
        """设置根日志器"""
        if self._root_handler_added:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # 清除已有的处理器
        root_logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter(
            fmt=self.log_format,
            datefmt=self.log_date_format,
        )

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        self._root_handler_added = True

    def get_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的日志器

        Args:
            name: 日志器名称

        Returns:
            logging.Logger 实例
        """
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)

        if self.log_dir:
            self._add_file_handler(logger)

        self._loggers[name] = logger
        return logger

    def _add_file_handler(self, logger: logging.Logger):
        """为日志器添加文件处理器"""
        formatter = logging.Formatter(
            fmt=self.log_format,
            datefmt=self.log_date_format,
        )

        # 日志文件路径
        log_file = os.path.join(self.log_dir, f"{logger.name}.log")

        # 使用 RotatingFileHandler 实现日志轮转
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        cls._instance = None
        cls._loggers.clear()


# 全局函数，简化日志获取
def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器

    Args:
        name: 日志器名称

    Returns:
        logging.Logger 实例
    """
    manager = LoggerManager.get_instance()
    return manager.get_logger(name)


def init_logs(
    log_dir: str,
    log_level: int = logging.INFO,
    log_format: str = None,
    log_date_format: str = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
):
    """
    初始化全局日志配置

    Args:
        log_dir: 日志文件目录
        log_level: 日志级别
        log_format: 日志格式
        log_date_format: 日期格式
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量
    """
    if log_format is None:
        log_format = _DEFAULT_LOG_FORMAT_
    if log_date_format is None:
        log_date_format = _DEFAULT_LOG_DATE_FORMAT_

    manager = LoggerManager.get_instance()
    manager.init(
        log_dir=log_dir,
        log_level=log_level,
        log_format=log_format,
        log_date_format=log_date_format,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


# 便捷函数：设置日志目录
def setup_logs(log_dir: str = None):
    """
    设置日志目录并初始化日志系统

    Args:
        log_dir: 日志文件目录，默认使用 /app/media/logs
    """
    if log_dir is None:
        log_dir = os.getenv("MEDIA_PATH", "/app/media")
        log_dir = os.path.join(log_dir, "logs")

    init_logs(log_dir)


# 示例用法
if __name__ == "__main__":
    # 初始化日志系统
    setup_logs("/tmp/logs")

    # 获取日志器
    logger = get_logger(__name__)

    # 测试日志输出
    logger.debug("这是 debug 日志")
    logger.info("这是 info 日志")
    logger.warning("这是 warning 日志")
    logger.error("这是 error 日志")
