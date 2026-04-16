#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/15 11:36:58
Version: 1.0.0
Description: 数据库管理
"""
import os
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import dataset

# 数据库表名
_TABLE_NAME_ = "p123_fast_link"


# 状态枚举
class FileStatus:
    """文件状态枚举"""

    INIT = 0  # 初始化
    UPLOADING = 1  # 上传中
    UPLOADED = 2  # 已上传
    FAILED = 3  # 上传失败


@dataclass
class P123FastLink:
    """p123_fast_link 数据模型"""

    p_id: Optional[int] = None
    path: str = ""
    size: int = 0
    md5: str = ""
    is_base62: bool = False
    create_at: int = 0
    update_at: int = 0
    status: int = FileStatus.INIT
    remark: str = ""

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "P123FastLink":
        """从数据库行创建实例"""
        if row is None:
            return None
        return cls(
            p_id=row.get("id"),
            path=row.get("path", ""),
            size=row.get("size", 0),
            md5=row.get("md5", ""),
            is_base62=bool(row.get("is_base62", False)),
            create_at=row.get("create_at", 0),
            update_at=row.get("update_at", 0),
            status=row.get("status", FileStatus.INIT),
            remark=row.get("remark", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "path": self.path,
            "size": self.size,
            "md5": self.md5,
            "is_base62": self.is_base62,
            "create_at": self.create_at,
            "update_at": self.update_at,
            "status": self.status,
            "remark": self.remark,
        }


class Database:
    """数据库管理类"""

    _instance: Optional["Database"] = None

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径，默认使用 /media/data/p123_fast_link.db
        """
        if db_path is None:
            media_path = os.getenv("MEDIA_PATH", "/media")
            db_dir = os.path.join(media_path, "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "p123_fast_link.db")

        self.db_path = db_path
        self.db = dataset.connect(f"sqlite:///{db_path}")
        self._ensure_table()

    @classmethod
    def get_instance(cls, db_path: str = None) -> "Database":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def _ensure_table(self):
        """确保表存在"""
        if _TABLE_NAME_ not in self.db.tables:
            self.db.create_table(_TABLE_NAME_, primary_id="id", primary_increment=True)

    @property
    def table(self):
        """获取表对象"""
        return self.db[_TABLE_NAME_]

    # ==================== 增删改查操作 ====================

    def insert(self, link: P123FastLink) -> int:
        """
        插入记录

        Args:
            link: P123FastLink 实例

        Returns:
            插入记录的 id
        """
        data = link.to_dict()
        data["create_at"] = int(time.time())
        data["update_at"] = int(time.time())
        row = self.table.insert(data)
        # dataset 库返回的可能是整数或字典
        if isinstance(row, dict):
            return row["id"]
        return row

    def update(self, _id: int, **kwargs) -> bool:
        """
        更新记录

        Args:
            _id: 记录 id
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        kwargs["update_at"] = int(time.time())
        # 需要在 kwargs 中添加 id 字段
        kwargs["id"] = _id
        self.table.update(kwargs, keys=["id"])
        return True

    def delete(self, _id: int) -> bool:
        """
        删除记录

        Args:
            _id: 记录 id

        Returns:
            是否删除成功
        """
        self.table.delete(id=_id)
        return True

    def get_by_id(self, _id: int) -> Optional[P123FastLink]:
        """
        根据 id 获取记录

        Args:
            _id: 记录 id

        Returns:
            P123FastLink 实例或 None
        """
        row = self.table.find_one(id=_id)
        return P123FastLink.from_row(row)

    def get_by_path(self, path: str) -> Optional[P123FastLink]:
        """
        根据文件路径获取记录

        Args:
            path: 文件路径

        Returns:
            P123FastLink 实例或 None
        """
        row = self.table.find_one(path=path)
        return P123FastLink.from_row(row)

    def get_by_md5(self, md5: str) -> Optional[P123FastLink]:
        """
        根据 md5 获取记录

        Args:
            md5: 文件 md5

        Returns:
            P123FastLink 实例或 None
        """
        row = self.table.find_one(md5=md5)
        return P123FastLink.from_row(row)

    def get_by_status(self, status: int, limit: int = 100) -> List[P123FastLink]:
        """
        根据状态获取记录列表

        Args:
            status: 文件状态
            limit: 返回数量限制

        Returns:
            P123FastLink 实例列表
        """
        rows = self.table.find(status=status, order_by=["-id"], _limit=limit)
        return [P123FastLink.from_row(row) for row in rows]

    def get_all(self, limit: int = 1000, offset: int = 0) -> List[P123FastLink]:
        """
        获取所有记录

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            P123FastLink 实例列表
        """
        rows = self.table.all(order_by=["-id"], _limit=limit, _offset=offset)
        return [P123FastLink.from_row(row) for row in rows]

    def count(self, status: int = None) -> int:
        """
        统计记录数量

        Args:
            status: 如果指定，则统计指定状态的记录数

        Returns:
            记录数量
        """
        if status is not None:
            return self.table.count(status=status)
        return self.table.count()

    def exists(self, path: str = None, md5: str = None) -> bool:
        """
        检查记录是否存在

        Args:
            path: 文件路径
            md5: 文件 md5

        Returns:
            是否存在
        """
        if path:
            return self.table.find_one(path=path) is not None
        if md5:
            return self.table.find_one(md5=md5) is not None
        return False

    def upsert(self, link: P123FastLink) -> int:
        """
        插入或更新记录（如果存在则更新，不存在则插入）

        Args:
            link: P123FastLink 实例

        Returns:
            记录 id
        """
        existing = self.get_by_path(link.path)
        if existing:
            self.update(existing.p_id, **link.to_dict())
            return existing.p_id
        else:
            return self.insert(link)

    def close(self):
        """关闭数据库连接"""
        self.db.close()


# 全局数据库实例
_db: Optional[Database] = None


def get_database(db_path: str = None) -> Database:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = Database.get_instance(db_path)
    return _db
