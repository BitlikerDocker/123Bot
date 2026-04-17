#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/13 17:45:31
Version: 1.0.0
Description: 123盘处理
See: https://github.com/ChenyangGao/p123client
"""
import os
import dataclasses
from typing import Optional

from p123client import P123Client
from p123client.client import check_response
from .config import Config


@dataclasses.dataclass
class Pan123File:
    """123 网盘文件信息"""

    name: str
    file_id: int
    parent_id: int
    is_dir: bool
    size: int = 0

    def is_file(self) -> bool:
        """判断是否是文件"""
        return not self.is_dir


class Pan123Client(object):
    """123 网盘客户端（手机号+密码登录）"""

    def __init__(self, cft: Config):

        if not cft.p123_username or not cft.p123_password:
            raise ValueError("账号不能为空，请在环境变量 PHONE 和 PASSWORD 中配置")
        print(f"获取历史token: {cft.p123_token}")
        need_login = True
        try:
            if not cft.p123_token:
                raise FileNotFoundError("历史token不存在，需要登录")
            self.client = P123Client(token=cft.p123_token)
            self.list_dir()  # 验证token是否有效
            need_login = False
        except Exception as e:
            print(f"历史token无效，重新登录: {e}")
        if not need_login:
            return
        self.client = P123Client(passport=cft.p123_username, password=cft.p123_password)
        cft.p123_token = self.client.token
        cft.save_to_file()
        print(f"登录成功，欢迎 {cft.p123_username} [{cft.p123_token}]")

    def list_dir(self, parent_id: int = 0) -> list[Pan123File]:
        """列出目录下的文件和文件夹"""
        page = 1
        items: list[dict] = []

        while True:
            resp = check_response(
                self.client.fs_list_new({"parentFileId": parent_id, "Page": page})
            )
            data = resp.get("data", {})
            page_items = data.get("InfoList", [])
            items.extend(page_items)

            if data.get("Next") == "-1":
                break
            page += 1

        result: list[Pan123File] = []
        for info in items:
            # Type == 1 代表目录，Type == 0 代表文件
            is_dir = int(info.get("Type", 0)) == 1
            result.append(
                Pan123File(
                    name=info.get("FileName", ""),
                    file_id=int(info.get("FileId", 0)),
                    parent_id=int(info.get("ParentFileId", 0)),
                    is_dir=is_dir,
                    size=int(info.get("Size") or 0),
                )
            )
        return result

    def mkdir(self, name: str, parent_id: int = 0, duplicate: int = 0) -> dict:
        """创建目录"""
        resp = check_response(
            self.client.fs_mkdir(name, parent_id=parent_id, duplicate=duplicate)
        )
        data = resp.get("data", {})
        return data.get("Info") or data

    def _find_dir_id(self, name: str, parent_id: int) -> Optional[int]:
        """在 parent_id 下查找目录并返回 file_id"""
        for item in self.list_dir(parent_id):
            if item.is_dir and item.name == name:
                return item.file_id
        return None

    def ensure_dir(self, remote_dir: str, parent_id: int = 0) -> int:
        """确保 remote_dir 存在，返回目录 id"""
        current_parent_id = parent_id
        parts = [p for p in remote_dir.split("/") if p]

        for part in parts:
            found_id = self._find_dir_id(part, current_parent_id)
            if found_id is not None:
                current_parent_id = found_id
                continue

            created = self.mkdir(part, parent_id=current_parent_id, duplicate=0)
            current_parent_id = int(created.get("FileId", 0))
            if current_parent_id <= 0:
                raise RuntimeError(f"创建目录失败: {part}")

        return current_parent_id

    def upload_file(
        self,
        local_path: str,
        parent_id: int = 0,
        remote_name: str = "",
        duplicate: int = 1,
    ) -> dict:
        """上传本地文件到指定目录 id"""
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"本地文件不存在: {local_path}")

        if not remote_name:
            remote_name = os.path.basename(local_path)

        resp = check_response(
            self.client.upload_file(
                file=local_path,
                file_name=remote_name,
                parent_id=parent_id,
                duplicate=duplicate,
            )
        )

        data = resp.get("data", {})
        # 常见字段为 Info，也可能是 file_info
        return data.get("Info") or data.get("file_info") or data

    def upload_by_md5(
        self,
        file_md5: str,
        file_name: str,
        file_size: int,
        parent_id: int = 0,
        duplicate: int = 1,
    ) -> dict:
        """通过 md5 秒传，不依赖本地文件"""
        md5 = file_md5.strip().lower()
        if len(md5) != 32:
            raise ValueError("file_md5 必须是 32 位 md5 字符串")
        if not file_name:
            raise ValueError("file_name 不能为空")
        if file_size < 0:
            raise ValueError("file_size 不能小于 0")

        resp = check_response(
            self.client.upload_file_fast(
                file_md5=md5,
                file_name=file_name,
                file_size=file_size,
                parent_id=parent_id,
                duplicate=duplicate,
            )
        )
        data = resp.get("data", {})
        return data.get("Info") or data.get("file_info") or data

    def upload_by_md5_to_path(
        self,
        file_md5: str,
        file_name: str,
        file_size: int,
        remote_dir: str,
        duplicate: int = 1,
        parent_id: int = 0,
    ) -> dict:
        """通过 md5 秒传到指定远程路径（自动创建目录）"""
        target_parent_id = self.ensure_dir(remote_dir, parent_id=parent_id)
        return self.upload_by_md5(
            file_md5=file_md5,
            file_name=file_name,
            file_size=file_size,
            parent_id=target_parent_id,
            duplicate=duplicate,
        )

    def upload_to_path(
        self,
        local_path: str,
        remote_dir: str,
        duplicate: int = 1,
        parent_id: int = 0,
        remote_name: str = "",
    ) -> dict:
        """上传本地文件到远程路径（自动创建目录）"""
        target_parent_id = self.ensure_dir(remote_dir, parent_id=parent_id)
        return self.upload_file(
            local_path=local_path,
            parent_id=target_parent_id,
            remote_name=remote_name,
            duplicate=duplicate,
        )
