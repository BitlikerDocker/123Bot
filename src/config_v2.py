#!/usr/bin/env python
# pylint: disable=E0401,W0718,W1203

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/15 11:19:52
Version: 1.0.0
Description: 实现配置获取
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any


_P123_USER_NAME_KEY_ = "P123_USER_NAME"
_P123_PASSWORD_KEY_ = "P123_PASSWORD"
_P123_PARENT_ID_KEY_ = "P123_PARENT_ID"
_TG_TOKEN_KEY_ = "TG_TOKEN"
_TG_USER_WHITE_LIST_KEY_ = "TG_USER_WHITE_LIST"
_MEDIA_PATH_KEY_ = "MEDIA_PATH"
_CONFIG_PATH_KEY_ = "MEDIA_PATH"

# ====================== 日志配置 ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class ConfigManager:
    """
    配置管理器，负责从环境变量和配置文件中加载配置
    支持自动创建配置文件和环境变量回退
    """

    def __init__(self):
        # 默认配置值
        self.def_config = {
            "p123_username": "",
            "p123_password": "",
            "p123_token": "",
            "p123_parent_id": 0,
            "tg_token": "",
            "tg_user_white_list": [],
            "media": "/media",
        }
        # 初始化配置
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """加载配置，优先从文件，其次从环境变量"""
        # 1. 首先获取 CONFIG_PATH
        config_path = self._get_env_value(_CONFIG_PATH_KEY_, "config.json")

        try:
            # 2. 尝试从配置文件加载
            if Path(config_path).exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                logger.info(f"成功从配置文件加载配置: {config_path}")

                # 验证必要字段
                self._validate_config()
            else:
                # 3. 配置文件不存在，从环境变量创建
                logger.warning(f"配置文件不存在: {config_path}")
                self.config = self._create_default_config()

                # 4. 写入配置文件
                self._save_config(config_path)
                logger.info(f"已创建新的配置文件: {config_path}")

            # 5. 确保目录存在
            self._ensure_directories(self.config)

        except Exception as e:
            logger.error(f"配置加载失败: {str(e)}")
            logger.info("使用默认配置")
            self.config = self._create_default_config()

    def _get_env_value(self, key: str, default: Any = None) -> Any:
        """从环境变量获取值"""
        value = os.getenv(key)
        if value is None:
            return default

        # 特殊处理白名单列表
        if key == "TG_USER_WHITE_LIST":
            return [item.strip() for item in value.split(",") if item.strip()]

        return value

    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认配置，优先从环境变量获取"""
        config = self.DEFAULT_CONFIG.copy()

        # 从环境变量获取配置
        for env_key, config_key in self.CONFIG_MAPPING.items():
            if config_key is None:  # CONFIG_PATH 特殊处理
                continue

            env_value = self._get_env_value(env_key)
            if env_value is not None and env_value != "":
                config[config_key] = env_value

        return config

    def _ensure_directories(self, config: Dict[str, Any]):
        """确保必要的目录存在"""
        directories = [
            config["media"],
            config["json_path"],
            config["archive_path"],
            config["fail_path"],
        ]

        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                logger.info(f"已创建/验证目录: {directory}")
            except Exception as e:
                logger.error(f"创建目录失败 {directory}: {str(e)}")
                raise

    def _validate_config(self):
        """验证配置的完整性和正确性"""
        required_fields = ["tg_token", "tg_user_white_list"]

        for field in required_fields:
            if field not in self.config or not self.config[field]:
                raise ValueError(f"缺少必要配置字段: {field}")

        # 验证白名单是否为列表
        if not isinstance(self.config["tg_user_white_list"], list):
            raise ValueError("tg_user_white_list 必须是列表类型")

        # 设置默认路径（如果未提供）
        if "media" not in self.config or not self.config["media"]:
            self.config["media"] = "/media"

        if "json_path" not in self.config or not self.config["json_path"]:
            self.config["json_path"] = f"{self.config['media']}/json"

        if "archive_path" not in self.config or not self.config["archive_path"]:
            self.config["archive_path"] = f"{self.config['media']}/archive"

        if "fail_path" not in self.config or not self.config["fail_path"]:
            self.config["fail_path"] = f"{self.config['media']}/fail"

    def _save_config(self, config_path: str):
        """保存配置到文件"""
        try:
            config_dir = Path(config_path).parent
            if not config_dir.exists():
                config_dir.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到: {config_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            raise

    # ====================== 配置访问方法 ======================

    @property
    def USER_NAME(self) -> str:
        """123盘手机号码"""
        return self.config.get("123_username", "")

    @property
    def PASSWORD(self) -> str:
        """123盘密码"""
        return self.config.get("123_password", "")

    @property
    def TG_TOKEN(self) -> str:
        """Telegram bot token"""
        return self.config.get("tg_token", "")

    @property
    def TG_USER_WHITE_LIST(self) -> List[str]:
        """Telegram 白名单用户ID列表"""
        white_list = self.config.get("tg_user_white_list", [])
        return [str(user_id).strip() for user_id in white_list if str(user_id).strip()]

    @property
    def MEDIA(self) -> str:
        """媒体根目录"""
        return self.config.get("media", "/media")

    @property
    def JSON_PATH(self) -> str:
        """JSON文件目录"""
        return self.config.get("json_path", f"{self.MEDIA}/json")

    @property
    def ARCHIVE_PATH(self) -> str:
        """归档目录（已完成上传）"""
        return self.config.get("archive_path", f"{self.MEDIA}/archive")

    @property
    def FAIL_PATH(self) -> str:
        """失败文件目录"""
        return self.config.get("fail_path", f"{self.MEDIA}/fail")

    @property
    def CONFIG_PATH(self) -> str:
        """配置文件路径"""
        return self._get_env_value("CONFIG_PATH", "config.json")

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置（字典形式）"""
        return {
            "USER_NAME": self.USER_NAME,
            "PASSWORD": self.PASSWORD,
            "TG_TOKEN": self.TG_TOKEN,
            "TG_USER_WHITE_LIST": self.TG_USER_WHITE_LIST,
            "MEDIA": self.MEDIA,
            "JSON_PATH": self.JSON_PATH,
            "ARCHIVE_PATH": self.ARCHIVE_PATH,
            "FAIL_PATH": self.FAIL_PATH,
            "CONFIG_PATH": self.CONFIG_PATH,
        }

    def __str__(self) -> str:
        """返回配置的字符串表示（隐藏敏感信息）"""
        safe_config = self.config.copy()

        # 隐藏敏感信息
        sensitive_fields = ["123_password", "tg_token", "123_token"]
        for field in sensitive_fields:
            if field in safe_config and safe_config[field]:
                safe_config[field] = "*" * len(safe_config[field])

        return json.dumps(safe_config, indent=2, ensure_ascii=False)


# ====================== 单例模式 ======================
# 创建全局配置实例
config = ConfigManager()

# ====================== 使用示例 ======================
if __name__ == "__main__":
    # 测试配置加载
    logger.info("当前配置:")
    logger.info(str(config))

    logger.info("\n配置详情:")
    logger.info(f"用户名: {config.USER_NAME}")
    logger.info(f"白名单用户: {config.TG_USER_WHITE_LIST}")
    logger.info(f"JSON路径: {config.JSON_PATH}")
    logger.info(f"归档路径: {config.ARCHIVE_PATH}")
    logger.info(f"失败路径: {config.FAIL_PATH}")

    # 验证目录是否创建
    for path_name, path_value in [
        ("JSON_PATH", config.JSON_PATH),
        ("ARCHIVE_PATH", config.ARCHIVE_PATH),
        ("FAIL_PATH", config.FAIL_PATH),
    ]:
        exists = Path(path_value).exists()
        logger.info(f"{path_name} ({path_value}): {'✓ 存在' if exists else '✗ 不存在'}")
