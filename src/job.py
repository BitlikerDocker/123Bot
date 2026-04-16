#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/16 11:28:07
Version: 1.0.0
Description: 任务管理器 - 单例实现
"""
from enum import Enum
from threading import Lock
from typing import Dict, Any, Optional


class JobType(Enum):
    """任务类型"""
    JSON_TO_DB = "json_to_db"
    UPLOAD_BY_DB = "upload_by_db"


class JobStatus(Enum):
    """任务状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"


class JobManager:
    """单例任务管理器"""
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._instance:
            return
        self.status = JobStatus.IDLE
        self.current_job: Optional[Dict[str, Any]] = None
        self.pending_job: Optional[Dict[str, Any]] = None
        self._job_lock = Lock()
        self._instance = True

    def is_running(self) -> bool:
        """检查是否有任务正在运行"""
        return self.status == JobStatus.RUNNING

    def start_job(self, job_type: JobType, **kwargs) -> bool:
        """启动任务，如果有任务正在运行则保存为待执行任务，返回是否成功启动"""
        with self._job_lock:
            if self.status == JobStatus.RUNNING:
                # 保存待执行任务
                self.pending_job = {"type": job_type, "kwargs": kwargs}
                return False
            self.status = JobStatus.RUNNING
            self.current_job = {"type": job_type, "kwargs": kwargs}
            return True

    def complete_job(self) -> Optional[Dict[str, Any]]:
        """完成当前任务，如有待执行任务则自动转为当前任务"""
        with self._job_lock:
            self.status = JobStatus.COMPLETED
            self.current_job = None
            
            # 检查是否有待执行任务
            if self.pending_job:
                pending = self.pending_job
                self.pending_job = None
                self.status = JobStatus.RUNNING
                self.current_job = pending
                return pending
            
            self.status = JobStatus.IDLE
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取任务状态"""
        with self._job_lock:
            return {
                "status": self.status.value,
                "current_job": self.current_job,
                "pending_job": self.pending_job
            }
