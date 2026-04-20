#!/usr/bin/env python
# pylint: disable=E0401,W0718
"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/14 09:03:52
Version: 1.2.0
Description: 123 妙传脚本
123网盘秒传批量上传工具 (json导入)
json文件格式示例：

1. 头部字段：
"usesBase62EtagsInExport": true,
"commonPath": "根目录/",
"totalFilesCount": 459,
"totalSize": 1398185874665,

2. files 列表字段：
"path": "dir/file.mkv",
"size": "867071302",
...
usesBase62EtagsInExport=true 时：
"etag": "3xrsuPs9x8mM59QJAToVf"
usesBase62EtagsInExport=false 时：
"etag": "242500524fcc5d58ff7d2078cd409c"
or:
"sha1": "86B066225E66AA0DBABAF942555D00F850BE1382"

"""

import os
import time
import json
from typing import Tuple, List
from p123_client import Pan123Client
from config import (
    P123FastLink,
    get_database,
    FileStatus,
    get_config,
    Config,
    get_logger,
)


# 日志配置
logger = get_logger(__name__)


class _EtagConverter:
    """ETag 转换工具类，提供 Base62/Hex ETag 到标准 MD5 的转换功能"""

    BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    @classmethod
    def to_md5(cls, optimized_etag: str) -> str:
        """将 Base62 / Hex ETag 转换为标准的 32 位 Hex MD5

        Args:
            optimized_etag (str): ETag 字符串 (Base62 或 Hex)

        Returns:
            str: 32 位小写十六进制 MD5 字符串
        """
        if not optimized_etag or not isinstance(optimized_etag, str):
            raise ValueError("ETag cannot be empty")

        # 如果已经是 Hex 格式，直接返回
        if cls._is_valid_hex_(optimized_etag):
            return optimized_etag.lower()

        # 如果是 Base62 格式，转换为 Hex
        if cls._is_valid_base62_(optimized_etag):
            return cls._base62_to_hex_(optimized_etag)

        raise ValueError(f"Invalid ETag format: {optimized_etag}")

    @staticmethod
    def _is_valid_hex_(s: str) -> bool:
        """检查是否是有效的十六进制格式"""
        if not s or not isinstance(s, str):
            return False
        try:
            int(s, 16)
            return True
        except ValueError:
            return False

    @classmethod
    def _is_valid_base62_(cls, s: str) -> bool:
        """检查是否是有效的 Base62 格式"""
        if not s or not isinstance(s, str):
            return False
        return all(c in cls.BASE62_CHARS for c in s)

    @classmethod
    def _base62_to_hex_(cls, optimized_etag: str) -> str:
        """将 Base62 字符串转换为十六进制字符串"""
        # 将 Base62 字符串转换为大整数
        num = 0
        for char in optimized_etag:
            num = num * 62 + cls.BASE62_CHARS.index(char)

        # 转换为十六进制字符串
        hex_str = format(num, "x").lower()

        # 补零到 32 位
        if len(hex_str) < 32:
            hex_str = hex_str.zfill(32)

        return hex_str


class _JsonFileParser:
    """JSON 文件解析器，用于解析 123 网盘导出的文件列表"""

    @staticmethod
    def parse(json_path: str) -> list[P123FastLink]:
        """解析 json 文件，提取文件信息列表，支持两种格式

        支持格式1（原格式）:
        {
            "usesBase62EtagsInExport": true,
            "commonPath": "根目录/",
            "files": [{"etag": "...", "size": "...", "path": "..."}]
        }

        支持格式2（简化格式）:
        [[md5, size, path], [md5, size, path], ...]

        Args:
            json_path (str): json 文件路径

        Returns:
            list[P123FastLink]: 文件信息列表
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        file_info_list = []

        # 检查是否为简化格式（数组格式）
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            # 简化格式：[[md5, size, path], ...]
            for item in data:
                if len(item) >= 3:
                    md5 = item[0]
                    size = int(item[1])
                    path = item[2]
                    file_info_list.append(
                        P123FastLink(
                            md5=md5,
                            size=size,
                            path=path,
                            is_base62=False,
                        )
                    )
        else:
            # 原格式：{"usesBase62EtagsInExport": ..., "commonPath": ..., "files": [...]}
            uses_base62 = data.get("usesBase62EtagsInExport", False)
            common_path = data.get("commonPath", "")
            files = data.get("files", [])
            for file in files:
                etag = file["etag"]
                size = int(file["size"])
                path = file["path"]
                # 如果文件级别没有 usesBase62EtagsInExport 字段，则使用全局的设置
                file_uses_base62 = (
                    uses_base62
                    if ("usesBase62EtagsInExport" not in file)
                    else file["usesBase62EtagsInExport"]
                )
                md5 = etag if not file_uses_base62 else _EtagConverter.to_md5(etag)
                file_info_list.append(
                    P123FastLink(
                        md5=md5,
                        size=size,
                        path=os.path.join(common_path, path).replace("\\", "/"),
                        is_base62=file_uses_base62,
                    )
                )

        return file_info_list


class Pan123Uploader:
    """123 网盘上传器，提供文件上传和批量上传功能"""

    def __init__(self, upload_interval: float = 0.5):
        """初始化上传器

        Args:
            parent_id (int, optional): 上传的根目录 id. Defaults to 0.
            upload_interval (float, optional): 上传间隔时间(秒)，避免请求过快. Defaults to 0.5.
        """
        self._cft_: Config = get_config()
        self.parent_id = self._cft_.p123_parent_id
        self.upload_interval = upload_interval
        self.client = Pan123Client(self._cft_)

    def _move_to_target_dir(self, file_path: str, target_dir: str) -> str:
        """将文件移动到目标目录，若同名则追加时间戳"""
        os.makedirs(target_dir, exist_ok=True)
        base_name = os.path.basename(file_path)
        target_path = os.path.join(target_dir, base_name)

        if os.path.abspath(file_path) == os.path.abspath(target_path):
            return target_path

        if os.path.exists(target_path):
            name, ext = os.path.splitext(base_name)
            target_path = os.path.join(
                target_dir, f"{name}_{int(time.time() * 1000000)}{ext}"
            )

        os.replace(file_path, target_path)
        return target_path

    def json_to_db_batch(self, json_dir: str) -> Tuple[bool, str]:
        """将指定目录下的所有 json 文件解析到数据库中（事务方式）

        Args:
            json_dir (str): 包含 json 文件的目录路径

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息或成功消息)
        """
        try:
            # 获取目录下所有 json 文件路径
            json_paths = [
                os.path.join(json_dir, f)
                for f in os.listdir(json_dir)
                if f.lower().endswith(".json") or f.lower().endswith(".txt")
            ]
            if not json_paths:
                return False, "指定目录下没有找到任何 JSON 文件"

            # 调用单文件解析方法进行批量处理
            is_ok = False
            message_total = ""
            for json_path in json_paths:
                is_ok, message = self.json_to_db(json_path)
                if not is_ok:
                    logger.error(f"处理文件失败: {json_path}, error: {message}")
                else:
                    logger.info(f"成功处理文件: {json_path}, message: {message}")
                    message_total += f"{os.path.basename(json_path)}: {message}\n"

            return is_ok, message_total

        except FileNotFoundError as e:
            return False, f"目录不存在: {e}"
        except Exception as e:
            return False, f"处理过程中发生错误: {e}"

    def json_to_db(self, json_path: str) -> Tuple[bool, str]:
        """将json文件解析到db中（事务方式）

        Args:
            json_path (str): json文档路径

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息或成功消息)
        """
        try:
            # 解析 JSON 文件
            file_info_list = _JsonFileParser.parse(json_path)
            if not file_info_list:
                self._move_to_target_dir(json_path, self._cft_.fail_path)
                return False, "JSON 文件中没有找到任何文件"

            # 获取数据库实例
            db = get_database()
            inserted_count = 0

            # 开启事务，批量插入
            db.db.begin()
            try:
                for link in file_info_list:
                    # 检查是否已存在（根据 path）
                    existing = db.get_by_path(link.path)
                    if existing:
                        # 如果已存在，跳过或更新
                        continue
                    db.insert(link)
                    inserted_count += 1
                # 提交事务
                db.db.commit()
                # 插入成功, 将文件移动到已归档目录
                self._move_to_target_dir(json_path, self._cft_.archive_path)
                return True, f"成功插入 {inserted_count} 条记录到数据库"
            except Exception as e:
                # 回滚事务
                db.db.rollback()
                raise e

        except FileNotFoundError as e:
            return False, f"文件不存在: {e}"
        except json.JSONDecodeError as e:
            if os.path.exists(json_path):
                self._move_to_target_dir(json_path, self._cft_.fail_path)
            return False, f"JSON 解析失败: {e}"
        except Exception as e:
            if os.path.exists(json_path):
                self._move_to_target_dir(json_path, self._cft_.fail_path)
            return False, f"数据库操作失败: {e}"

    def json_to_db_batch2(self, json_paths: List[str]) -> Tuple[bool, str]:
        """将多个json文件解析到db中（事务方式）

        Args:
            json_paths (List[str]): json文档路径列表

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息或成功消息)
        """
        total_count = 0
        try:
            db = get_database()

            # 开启事务
            db.db.begin()
            try:
                for json_path in json_paths:
                    file_info_list = _JsonFileParser.parse(json_path)
                    for link in file_info_list:
                        existing = db.get_by_path(link.path)
                        if existing:
                            continue
                        db.insert(link)
                        total_count += 1
                    # 插入成功, 将文件移动到已归档目录
                    archive_dir = self._cft_.archive_path
                    self._move_to_target_dir(json_path, archive_dir)
                # 提交事务
                db.db.commit()

                return True, f"成功插入 {total_count} 条记录到数据库"
            except Exception as e:
                # 回滚事务
                db.db.rollback()
                raise e

        except FileNotFoundError as e:
            return False, f"文件不存在: {e}"
        except json.JSONDecodeError as e:
            return False, f"JSON 解析失败: {e}"
        except Exception as e:
            return False, f"数据库操作失败: {e}"

    def upload_by_db(
        self,
        status: int = FileStatus.INIT,
        limit: int = 100,
    ) -> Tuple[bool, str, dict]:
        """从数据库中读取待上传的文件进行秒传

        Args:
            status: 要处理的文件状态，默认处理 INIT 状态的文件
            limit: 每次处理的记录数限制

        Returns:
            Tuple[bool, str, dict]: (是否成功, 消息, 统计信息)
        """
        db = get_database()
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

        try:
            # 获取待处理的文件列表
            # 先尝试获取 INIT 状态的文件，如果为空则获取 FAILED 状态的文件
            file_list = db.get_by_status(status, limit=limit)
            if not file_list and status == FileStatus.INIT:
                file_list = db.get_by_status(FileStatus.FAILED, limit=limit)
            if not file_list:
                return True, "没有需要上传的文件", stats

            stats["total"] = len(file_list)

            # 开启事务
            db.db.begin()
            try:
                for link in file_list:
                    try:
                        # 更新状态为上传中
                        db.update(link.p_id, status=FileStatus.UPLOADING)

                        # 获取文件名和目录路径
                        file_name = os.path.basename(link.path)
                        remote_dir = os.path.dirname(link.path)

                        # 调用秒传 API
                        result = self.client.upload_by_md5_to_path(
                            file_md5=link.md5,
                            file_name=file_name,
                            file_size=link.size,
                            remote_dir=remote_dir,
                            parent_id=self.parent_id,
                        )

                        # 等待间隔时间
                        time.sleep(self.upload_interval)

                        # 检查秒传结果
                        upload_id = result.get("UploadId", "")
                        if upload_id:
                            # 秒传失败，需要后续分片上传
                            db.update(
                                link.p_id,
                                status=FileStatus.FAILED,
                                remark=f"秒传失败，需要分片上传，UploadId: {upload_id}",
                            )
                            logger.warning(
                                f"秒传失败: {link.path}, size={link.size}, "
                                f"UploadId={upload_id}"
                            )
                            stats["failed"] += 1
                        else:
                            # 秒传成功
                            db.update(link.p_id, status=FileStatus.UPLOADED)
                            logger.info(f"上传成功: {link.path}, size={link.size}")
                            stats["success"] += 1

                    except Exception as e:
                        # 单个文件上传失败
                        db.update(
                            link.p_id,
                            status=FileStatus.FAILED,
                            remark=f"上传异常: {str(e)}",
                        )
                        logger.error(
                            f"上传异常: {link.path}, size={link.size}, error={e}"
                        )
                        stats["failed"] += 1

                # 提交事务
                db.db.commit()

            except Exception as e:
                # 回滚事务
                db.db.rollback()
                raise e

            message = (
                f"上传完成: 成功 {stats['success']}, "
                f"失败 {stats['failed']}, "
                f"跳过 {stats['skipped']}"
            )
            return True, message, stats

        except Exception as e:
            return False, f"上传过程发生错误: {e}", stats
