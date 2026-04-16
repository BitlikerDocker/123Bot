#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/16 11:28:07
Version: 1.0.0
Description: Telegram Bot 主程序
"""
import os
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import get_config, get_database
from p123_link import Pan123Uploader
from job import JobManager, JobType

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化全局变量
_cft_ = get_config()
_db_ = get_database(os.path.join(_cft_.media_path, "config", "db.sqlite3"))
_job_manager_ = JobManager()
_uploader_ = Pan123Uploader()

# 设置媒体路径
os.environ["MEDIA_PATH"] = _cft_.media_path
MEDIA_PATH = _cft_.media_path
JSON_PATH = _cft_.json_path
WEB_SITE = _cft_.web_site

# 确保目录存在
Path(JSON_PATH).mkdir(parents=True, exist_ok=True)

logger.info(f"config: {_cft_}")
logger.info(f"JSON_PATH: {JSON_PATH}")


def _check_user_whitelist(user_id: int) -> bool:
    """检查用户是否在白名单中"""
    whitelist = _cft_.tg_user_white_list
    if not whitelist:  # 为空允许所有用户
        return True
    return user_id in whitelist


def _get_error_message(user_id: int) -> str:
    """获取用户不支持的错误消息"""
    return (
        f"当前用户({user_id})不支持, 请查看USER_WHITE_LIST变量是否包含当前用户id;"
        f"详情使用教程请参考{WEB_SITE}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """开始命令"""
    user_id = update.effective_user.id

    if not _check_user_whitelist(user_id):
        await update.message.reply_text(_get_error_message(user_id))
        return

    await update.message.reply_text(
        f"欢迎使用 123Bot 快速秒传工具, 详情使用教程请参考{WEB_SITE}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """帮助命令"""
    user_id = update.effective_user.id

    if not _check_user_whitelist(user_id):
        await update.message.reply_text(_get_error_message(user_id))
        return

    await update.message.reply_text(f"详情使用教程请参考{WEB_SITE}")


async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """上传命令"""
    user_id = update.effective_user.id

    if not _check_user_whitelist(user_id):
        await update.message.reply_text(_get_error_message(user_id))
        return

    if _job_manager_.is_running():
        await update.message.reply_text("当前任务正在进行中，请稍候...")
        return

    # 启动上传任务
    if _job_manager_.start_job(JobType.UPLOAD_BY_DB):
        await update.message.reply_text("上传任务已启动...")

        try:
            _uploader_.upload_by_db(limit=10)
            next_job = _job_manager_.complete_job()
            await update.message.reply_text("上传任务已完成")

            # 如果有待执行任务，继续执行
            if next_job:
                logger.info(f"执行待执行任务: {next_job}")
        except Exception as e:
            logger.error(f"上传任务失败: {e}")
            _job_manager_.complete_job()
            await update.message.reply_text(f"上传任务失败: {str(e)}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """查看任务状态"""
    user_id = update.effective_user.id

    if not _check_user_whitelist(user_id):
        await update.message.reply_text(_get_error_message(user_id))
        return

    status_info = _job_manager_.get_status()
    status_text = (
        f"当前任务状态:\n"
        f"- 状态: {status_info['status']}\n"
        f"- 当前任务: {status_info['current_job']}\n"
        f"- 待执行任务: {status_info['pending_job']}"
    )
    await update.message.reply_text(status_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理消息"""
    user_id = update.effective_user.id

    if not _check_user_whitelist(user_id):
        await update.message.reply_text(_get_error_message(user_id))
        return

    # 检查消息中的文件
    if update.message.document:
        file_name = update.message.document.file_name

        if file_name.endswith((".json", ".txt")):
            try:
                file = await context.bot.get_file(update.message.document.file_id)
                file_path = os.path.join(JSON_PATH, file_name)
                await file.download_to_drive(file_path)

                logger.info(f"文件已下载: {file_path}")
                await update.message.reply_text(f"文件 {file_name} 已接收，等待处理...")

                # 启动 json_to_db 任务
                if _job_manager_.start_job(JobType.JSON_TO_DB, file_path=file_path):
                    try:
                        ok, msg = _uploader_.json_to_db(file_path)
                        next_job = _job_manager_.complete_job()
                        await update.message.reply_text(f"处理结果: {msg}")

                        # 如果有待执行任务，继续执行
                        if next_job:
                            logger.info(f"执行待执行任务: {next_job}")
                    except Exception as e:
                        logger.error(f"处理文件失败: {e}")
                        _job_manager_.complete_job()
                        await update.message.reply_text(f"处理文件失败: {str(e)}")
                else:
                    await update.message.reply_text(
                        "当前有任务正在进行，文件已保存，将在任务完成后处理"
                    )

            except Exception as e:
                logger.error(f"下载文件失败: {e}")
                await update.message.reply_text(f"下载文件失败: {str(e)}")


def main() -> None:
    """启动 Bot"""
    token = _cft_.tg_token

    if not token:
        logger.error("Telegram Bot Token 未配置")
        return

    # 创建应用
    application = Application.builder().token(token).build()

    # 添加命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("status", status_command))

    # 添加消息处理器（必须在命令处理器之后）
    application.add_handler(MessageHandler(filters.Document.ALL, handle_message))

    # 启动 Bot
    logger.info("Telegram Bot 启动中...")
    application.run_polling()


if __name__ == "__main__":
    main()
