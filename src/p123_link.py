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

    def __init__(self, json_path: str):
        """初始化解析器

        Args:
            json_path (str): json 文件路径
        """
        self.json_path = json_path
        self._data = None

    def parse(self) -> list[P123FastLink]:
        """解析 json 文件，提取文件信息列表

        Returns:
            list[FileInfo]: 文件信息列表
        """
        with open(self.json_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        uses_base62 = self._data.get("usesBase62EtagsInExport", False)
        common_path = self._data.get("commonPath", "")
        files = self._data.get("files", [])

        file_info_list = []
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

    def __init__(self, parent_id: int = 0, upload_interval: float = 0.5):
        """初始化上传器

        Args:
            parent_id (int, optional): 上传的根目录 id. Defaults to 0.
            upload_interval (float, optional): 上传间隔时间(秒)，避免请求过快. Defaults to 0.5.
        """
        self._cft_: Config = get_config()
        self.parent_id = self._cft_.p123_parent_id
        self.upload_interval = upload_interval
        self.client = Pan123Client(self._cft_)

    def json_to_db(self, json_path: str) -> Tuple[bool, str]:
        """将json文件解析到db中（事务方式）

        Args:
            json_path (str): json文档路径

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息或成功消息)
        """
        try:
            # 解析 JSON 文件
            file_info_list = _JsonFileParser(json_path).parse()
            if not file_info_list:
                return False, "JSON 文件中没有找到任何文件"

            # 获取数据库实例
            db = get_database()

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
                # 提交事务
                db.db.commit()
                # 插入成功, 将文件移动到已归档目录
                archive_dir = self._cft_.archive_path
                os.makedirs(archive_dir, exist_ok=True)
                archived_path = os.path.join(archive_dir, os.path.basename(json_path))
                os.rename(json_path, archived_path)
                return True, f"成功插入 {len(file_info_list)} 条记录到数据库"
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

    def json_to_db_batch(self, json_paths: List[str]) -> Tuple[bool, str]:
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
                    file_info_list = _JsonFileParser(json_path).parse()
                    for link in file_info_list:
                        existing = db.get_by_path(link.path)
                        if existing:
                            continue
                        db.insert(link)
                        total_count += 1

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
            file_list = db.get_by_status(status, limit=limit)
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

    # def upload_file(self, file_info: FileInfo) -> bool:
    #     """上传单个文件到 123 网盘

    #     Args:
    #         file_info (FileInfo): 文件信息对象

    #     Returns:
    #         bool: 上传是否成功
    #     """
    #     try:
    #         result = self.client.upload_by_md5_to_path(
    #             file_md5=file_info.md5,
    #             file_name=os.path.basename(file_info.path),
    #             file_size=file_info.size,
    #             remote_dir=os.path.dirname(file_info.path),
    #             parent_id=self.parent_id,
    #         )
    #         time.sleep(self.upload_interval)
    #         upload_id = result.get("UploadId", "")
    #         if upload_id:
    #             print(f"  -> 秒传失败，UploadId: {upload_id}")
    #             return False  # 提供上传id, 说明没有妙传成功过, 需要后续分片上传
    #         print(f"  -> 妙传成功: {file_info.path}")
    #         return True
    #     except Exception as e:
    #         print(f"上传失败: {file_info.path} -> {e}")
    #         return False

    # def upload_by_json(self, json_path: str) -> list[FileInfo]:
    #     """从 json 文件批量上传文件到 123 网盘

    #     Args:
    #         json_path (str): json 文件路径

    #     Returns:
    #         list[FileInfo]: 上传失败的文件信息列表
    #     """
    #     file_info_list = _JsonFileParser(json_path).parse()
    #     fail_list = []
    #     for file_info in file_info_list:
    #         print(
    #             f"正在上传: {file_info.path} (md5={file_info.md5}, size={file_info.size})"
    #         )
    #         success = self.upload_file(file_info)
    #         if not success:
    #             fail_list.append(file_info)
    #     return fail_list

    # @staticmethod
    # def save_fail_log(fail_list: list[FileInfo], output_path: str) -> None:
    #     """将失败文件列表保存为 JSON 格式的日志文件

    #     Args:
    #         fail_list (list[FileInfo]): 失败文件信息列表
    #         output_path (str): 日志文件输出路径
    #     """
    #     os.makedirs(os.path.dirname(output_path), exist_ok=True)
    #     log_data = {
    #         "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    #         "total_failures": len(fail_list),
    #         "usesBase62EtagsInExport": False,
    #         "commonPath": "",
    #         "files": [
    #             {
    #                 "path": file_info.path,
    #                 "md5": file_info.md5,
    #                 "size": file_info.size,
    #                 "usesBase62EtagsInExport": len(file_info.md5)
    #                 != 32,  # 根据 md5 长度判断是否为 base62
    #             }
    #             for file_info in fail_list
    #         ],
    #     }
    #     with open(output_path, "w", encoding="utf-8") as f:
    #         json.dump(log_data, f, ensure_ascii=False, indent=2)
