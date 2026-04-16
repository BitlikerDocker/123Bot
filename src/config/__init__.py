#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/03/31 16:45:29
Version: 1.0.0
Description: 配置入口
"""
from .config import Config, get_config
from .database import get_database, P123FastLink, FileStatus
from .logs import setup_logs, get_logger, init_logs
from .format import md_format_html

__all__ = [
    "Config",
    "get_config",
    "get_database",
    "P123FastLink",
    "FileStatus",
    "setup_logs",
    "get_logger",
    "init_logs",
    "md_format_html",
]
