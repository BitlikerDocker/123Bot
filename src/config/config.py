#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/14 17:08:42
Version: 1.0.0
Description: 系统配置获取
优先级:
config.json -> env
"""
import os
import json
from typing import List, Optional
import dataclasses

# 变量定义
_P123_USER_NAME_KEY_ = "P123_USER_NAME"
_P123_PASSWORD_KEY_ = "P123_PASSWORD"
_P123_PARENT_ID_KEY_ = "P123_PARENT_ID"
_TG_TOKEN_KEY_ = "TG_TOKEN"
_TG_USER_WHITE_LIST_KEY_ = "TG_USER_WHITE_LIST"
_IS_AUTO_UPLOAD_KEY_ = "IS_AUTO_UPLOAD"
_MEDIA_PATH_KEY_ = "MEDIA_PATH"
_CONFIG_PATH_KEY_ = "CONFIG_PATH"
_JSON_PATH_KEY_ = "JSON_PATH"
_ARCHIVE_PATH_KEY_ = "ARCHIVE_PATH"
_FAIL_PATH_KEY_ = "FAIL_PATH"


@dataclasses.dataclass
class Config:
    """配置信息"""

    # 123盘配置
    p123_username: str = ""  # 123盘手机号码
    p123_password: str = ""  # 123盘密码
    p123_parent_id: int = 0  # 123盘根目录
    p123_token: str = ""  # 123token

    # Telegram配置
    tg_token: str = ""  # telegram bot token
    tg_user_white_list: List[int] = dataclasses.field(
        default_factory=list
    )  # telegram白名单用户id列表
    is_auto_upload: bool = False  # 是否自动上传

    # 路径配置
    media_path: str = ""  # 媒体根目录
    json_path: str = ""  # json文件目录
    archive_path: str = ""  # 已完成上传的文件归档路径
    fail_path: str = ""  # 上传失败文件归档路径

    def save_to_file(self, config_path: str = None):
        """保存到文件"""
        if not config_path:
            config_path = _get_config_path_()
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            data = {
                "p123_username": self.p123_username,
                "p123_password": self.p123_password,
                "p123_token": self.p123_token,
                "tg_token": self.tg_token,
                "tg_user_white_list": self.tg_user_white_list,
                "is_auto_upload": self.is_auto_upload,
                "media_path": self.media_path,
                "json_path": self.json_path,
                "archive_path": self.archive_path,
                "fail_path": self.fail_path,
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def get_db_path(self) -> str:
        """获取数据库路径"""
        return os.path.join(self.media_path, "config", "db.sqlite3")


def _init_by_json_(config_path: str) -> Optional[Config]:
    """通过 config.json 初始化

    Args:
        config_path (str): 配置路径

    Returns:
        bool: 是否加载了config
    """
    config = Config()
    # 查看是否存在
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            white_list = data.get("tg_user_white_list", [])
            if isinstance(white_list, str):
                # 如果是字符串，按逗号分隔并转换为int
                white_list = [
                    int(x.strip()) for x in white_list.split(",") if x.strip()
                ]
            elif isinstance(white_list, list):
                white_list = [
                    int(x) if not isinstance(x, int) else x for x in white_list
                ]
            config.p123_username = data.get("p123_username", "")
            config.p123_password = data.get("p123_password", "")
            config.p123_token = data.get("p123_token", "")
            config.tg_token = data.get("tg_token", "")
            config.tg_user_white_list = white_list
            config.is_auto_upload = data.get("is_auto_upload", False)
            config.media_path = data.get("media_path", "")
            config.json_path = data.get("json_path", "")
            config.archive_path = data.get("archive_path", "")
            config.fail_path = data.get("fail_path", "")
        return config
    except Exception as e:
        print(f"读取配置文件失败: {e}, 使用默认配置")
        return None


def _init_by_env_(config: Config) -> tuple[bool, Config]:
    """
    应用环境变量覆盖配置

    环境变量列表:
    - P123_USERNAME: 123盘手机号码
    - P123_PASSWORD: 123盘密码
    - P123_TOKEN: 123token
    - TG_TOKEN: telegram bot token
    - TG_USER_WHITE_LIST: telegram白名单用户id（逗号分隔）
    - MEDIA: 媒体根目录
    - JSON_PATH: json文件目录
    - ARCHIVE_PATH: 归档路径
    - FAIL_PATH: 失败文件路径
    """

    has_load = False
    if not config.p123_username and os.getenv(_P123_USER_NAME_KEY_):
        has_load = True
        config.p123_username = os.getenv(_P123_USER_NAME_KEY_)

    if not config.p123_password and os.getenv(_P123_PASSWORD_KEY_):
        has_load = True
        config.p123_password = os.getenv(_P123_PASSWORD_KEY_)

    if not config.p123_parent_id and os.getenv(_P123_PARENT_ID_KEY_):
        has_load = True
        config.p123_parent_id = os.getenv(_P123_PARENT_ID_KEY_)

    if not config.tg_token and os.getenv(_TG_TOKEN_KEY_):
        has_load = True
        config.tg_token = os.getenv(_TG_TOKEN_KEY_)

    if not config.media_path and os.getenv(_MEDIA_PATH_KEY_):
        has_load = True
        config.media_path = os.getenv(_MEDIA_PATH_KEY_)

    if not config.json_path and os.getenv(_JSON_PATH_KEY_):
        has_load = True
        config.json_path = os.getenv(_JSON_PATH_KEY_)

    if not config.archive_path and os.getenv(_ARCHIVE_PATH_KEY_):
        has_load = True
        config.archive_path = os.getenv(_ARCHIVE_PATH_KEY_)

    if not config.fail_path and os.getenv(_FAIL_PATH_KEY_):
        has_load = True
        config.fail_path = os.getenv(_FAIL_PATH_KEY_)

    if not config.tg_user_white_list and os.getenv(_TG_USER_WHITE_LIST_KEY_):
        has_load = True
        white_list = os.getenv(_TG_USER_WHITE_LIST_KEY_)
        config.tg_user_white_list = [
            int(x.strip()) for x in white_list.split(",") if x.strip()
        ]

    # 设置默认值
    if not config.media_path:
        has_load = True
        config.media_path = _get_media_by_env_()

    if not config.json_path:
        has_load = True
        config.json_path = os.getenv(
            _JSON_PATH_KEY_, os.path.join(config.media_path, "json")
        )

    if not config.archive_path:
        has_load = True
        config.archive_path = os.getenv(
            _ARCHIVE_PATH_KEY_, os.path.join(config.media_path, "archive")
        )

    if not config.fail_path:
        has_load = True
        config.fail_path = os.getenv(
            _FAIL_PATH_KEY_, os.path.join(config.media_path, "fail")
        )

    return has_load, config


def _get_config_path_() -> str:
    """获取配置路径"""
    if os.getenv(_CONFIG_PATH_KEY_):
        config_path = os.path.join(os.getenv(_CONFIG_PATH_KEY_), "config.json")
    else:
        media_path = _get_media_by_env_()
        config_path = os.getenv(
            _CONFIG_PATH_KEY_, os.path.join(media_path, "config", "config.json")
        )

    if not os.path.exists(os.path.dirname(config_path)):
        os.makedirs(os.path.dirname(config_path), True)
    return config_path


def _get_media_by_env_() -> str:
    """获取媒体路径"""
    media_path = _get_media_by_env_()
    if not os.path.exists(media_path):
        os.makedirs(media_path, True)
    return media_path


_config_: Config = None


def get_config() -> Config:
    """获取Config"""
    global _config_
    if not _config_:
        # 1. 先通过json初始化数据
        config = _init_by_json_(config_path=_get_config_path_())
        # 2. 合并变量
        if not config:
            config = Config()
        has_load, config = _init_by_env_(config)
        if has_load:
            config.save_to_file()
        _config_ = config
    return _config_


if __name__ == "__main__":
    os.environ[_MEDIA_PATH_KEY_] = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "tmp"
    )
    print(os.getenv(_MEDIA_PATH_KEY_))
    _cft_ = get_config()
    print(f"config:\n{_cft_}")
