#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/16 11:28:07
Version: 2.0.0
Description: 任务管理器 - 单例实现，包含所有任务执行逻辑
"""
import threading
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Callable
from pathlib import Path

from p123_link import Pan123Uploader


class JobType(Enum):
    """任务类型"""

    JSON_TO_DB = "json_to_db"
    UPLOAD_BY_DB = "upload_by_db"


class JobStatus(Enum):
    """任务状态"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"


class JobTask:
    """单个任务"""

    def __init__(self, task_type: JobType, **kwargs):
        self.task_type = task_type
        self.kwargs = kwargs
        self.status = "pending"
        self.result = None
        self.error = None


class JobManager:
    """单例任务管理器 - 负责任务队列和执行"""

    _instance = None
    _initialized = False
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.status = JobStatus.IDLE
        self.current_job: Optional[JobTask] = None
        self.pending_jobs: list = []
        self._job_lock = threading.Lock()
        self._uploader = Pan123Uploader()

        # 回调函数列表
        self._on_finished_callbacks: list = []

        self._initialized = True

    def on_job_finished(self, callback: Callable):
        """注册任务完成回调"""
        self._on_finished_callbacks.append(callback)

    def submit_job(self, job_type: JobType, **kwargs) -> bool:
        """提交任务，如果有任务正在运行则加入待执行队列，返回是否立即执行"""
        with self._job_lock:
            task = JobTask(job_type, **kwargs)

            if self.status == JobStatus.RUNNING:
                # 正在运行，添加到待执行队列
                self.pending_jobs.append(task)
                return False

            # 开始执行
            self.status = JobStatus.RUNNING
            self.current_job = task
            return True

    def is_running(self) -> bool:
        """检查是否有任务正在运行"""
        with self._job_lock:
            return self.status == JobStatus.RUNNING

    def execute_current_job(self) -> Tuple[bool, str]:
        """执行当前任务，返回 (成功标志, 消息)"""
        with self._job_lock:
            if not self.current_job:
                return False, "没有待执行任务"

            task = self.current_job

        try:
            if task.task_type == JobType.JSON_TO_DB:
                return self._execute_json_to_db(task)
            elif task.task_type == JobType.UPLOAD_BY_DB:
                return self._execute_upload_by_db(task)
            else:
                return False, f"未知任务类型: {task.task_type}"
        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            with self._job_lock:
                if self.current_job == task:
                    self.current_job.error = str(e)
            return False, error_msg

    def _execute_json_to_db(self, task: JobTask) -> Tuple[bool, str]:
        """执行 json_to_db 任务"""
        file_path = task.kwargs.get("file_path")
        if not file_path:
            return False, "文件路径不存在"

        try:
            ok, msg = self._uploader.json_to_db(file_path)
            with self._job_lock:
                if self.current_job == task:
                    self.current_job.result = {"ok": ok, "msg": msg}
            return ok, msg
        except Exception as e:
            return False, str(e)

    def _execute_upload_by_db(self, task: JobTask) -> Tuple[bool, str]:
        """执行 upload_by_db 任务"""
        limit = task.kwargs.get("limit", 10)
        try:
            self._uploader.upload_by_db(limit=limit)
            msg = f"成功处理 {limit} 个文件"
            with self._job_lock:
                if self.current_job == task:
                    self.current_job.result = {"ok": True, "msg": msg}
            return True, msg
        except Exception as e:
            return False, str(e)

    def finish_current_job(
        self, success: bool = True, message: str = ""
    ) -> Optional[JobTask]:
        """完成当前任务，返回下一个待执行任务（如果有的话）"""
        with self._job_lock:
            if self.current_job:
                self.current_job.status = "completed"

            self.status = JobStatus.COMPLETED
            completed_job = self.current_job
            self.current_job = None

            # 检查是否有待执行任务
            if self.pending_jobs:
                next_task = self.pending_jobs.pop(0)
                self.status = JobStatus.RUNNING
                self.current_job = next_task

                # 触发回调
                for callback in self._on_finished_callbacks:
                    try:
                        callback(completed_job, success, message)
                    except Exception as e:
                        print(f"回调执行出错: {e}")

                return next_task

            self.status = JobStatus.IDLE

            # 触发回调
            for callback in self._on_finished_callbacks:
                try:
                    callback(completed_job, success, message)
                except Exception as e:
                    print(f"回调执行出错: {e}")

            return None

    def get_status(self) -> Dict[str, Any]:
        """获取任务状态"""
        with self._job_lock:
            current_job_info = None
            if self.current_job:
                current_job_info = {
                    "type": self.current_job.task_type.value,
                    "status": self.current_job.status,
                }

            pending_jobs_info = [
                {"type": task.task_type.value} for task in self.pending_jobs
            ]

            return {
                "status": self.status.value,
                "current_job": current_job_info,
                "pending_count": len(self.pending_jobs),
                "pending_jobs": pending_jobs_info,
            }

    def save_file(self, file_path: str, file_data: bytes) -> Tuple[bool, str]:
        """线程安全的文件保存"""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(file_data)
            return True, f"文件已保存到 {file_path}"
        except Exception as e:
            return False, f"文件保存失败: {str(e)}"
