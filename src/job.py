#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/16 11:28:07
Version: 1.0.0
Description: 任务管理器 - 单例实现
"""
from __future__ import annotations

import asyncio
import os
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, Optional

from src.config import get_config, get_logger
from src.p123_link import Pan123Uploader


logger = get_logger(__name__)


class JobType(Enum):
    """任务类型"""

    JSON_TO_DB = "json_to_db"
    UPLOAD_BY_DB = "upload_by_db"


class JobStatus(Enum):
    """任务状态"""

    IDLE = "idle"
    RUNNING = "running"


@dataclass
class JobItem:
    job_type: JobType
    kwargs: Dict[str, Any] = field(default_factory=dict)


class JobManager:
    """任务管理器 - 负责管理和执行上传相关的异步任务"""

    _instance: Optional["JobManager"] = None
    _instance_lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._config = get_config()
        self._uploader = Pan123Uploader()
        self._status = JobStatus.IDLE
        self._current_job: Optional[JobItem] = None
        self._pending_jobs: Deque[JobItem] = deque()
        self._last_message = ""
        self._run_task: Optional[asyncio.Task] = None
        self._state_lock = asyncio.Lock()

    async def submit(self, job_type: JobType, **kwargs) -> Dict[str, Any]:
        job = JobItem(job_type=job_type, kwargs=kwargs)
        async with self._state_lock:
            was_running = (
                self._status == JobStatus.RUNNING
                or self._current_job is not None
                or bool(self._pending_jobs)
            )
            self._pending_jobs.append(job)
            self._ensure_runner_locked()
            return {
                "queued": was_running,
                "running": self._status == JobStatus.RUNNING,
                "pending_count": len(self._pending_jobs),
            }

    async def submit_upload_flow(self, file_path: str | None = None) -> Dict[str, Any]:
        result = await self.submit(JobType.JSON_TO_DB, file_path=file_path)
        await self.submit(JobType.UPLOAD_BY_DB)
        return result

    async def get_status(self) -> Dict[str, Any]:
        async with self._state_lock:
            return {
                "status": self._status.value,
                "current_job": (
                    self._current_job.job_type.value if self._current_job else ""
                ),
                "pending_jobs": [job.job_type.value for job in self._pending_jobs],
                "pending_count": len(self._pending_jobs),
                "last_message": self._last_message,
            }

    def _ensure_runner_locked(self) -> None:
        if self._run_task is None or self._run_task.done():
            self._run_task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            async with self._state_lock:
                if not self._pending_jobs:
                    self._status = JobStatus.IDLE
                    self._current_job = None
                    self._run_task = None
                    return

                self._status = JobStatus.RUNNING
                self._current_job = self._pending_jobs.popleft()
                current_job = self._current_job

            try:
                message = await self._execute(current_job)
                async with self._state_lock:
                    self._last_message = message
            except Exception as exc:
                logger.exception("Job failed: %s", exc)
                async with self._state_lock:
                    self._last_message = f"{current_job.job_type.value} failed: {exc}"

    async def _execute(self, job: JobItem) -> str:
        if job.job_type == JobType.JSON_TO_DB:
            return await self._run_json_to_db(job.kwargs.get("file_path"))
        if job.job_type == JobType.UPLOAD_BY_DB:
            return await self._run_upload_by_db()
        raise ValueError(f"Unsupported job type: {job.job_type}")

    async def _run_json_to_db(self, file_path: str | None) -> str:
        if file_path:
            ok, message = await asyncio.to_thread(self._uploader.json_to_db, file_path)
            if not ok:
                raise RuntimeError(message)
            return message

        paths = self._scan_json_files()
        if not paths:
            return "未找到待处理的 json/txt 文件"

        ok, message = await asyncio.to_thread(self._uploader.json_to_db_batch, paths)
        if not ok:
            raise RuntimeError(message)
        return message

    async def _run_upload_by_db(self) -> str:
        ok, message, _stats = await asyncio.to_thread(self._uploader.upload_by_db)
        if not ok:
            raise RuntimeError(message)
        return message

    def _scan_json_files(self) -> list[str]:
        json_dir = Path(self._config.json_path)
        if not json_dir.exists():
            return []

        file_paths = []
        for entry in json_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in {".json", ".txt"}:
                continue
            file_paths.append(os.fspath(entry))
        return sorted(file_paths)
