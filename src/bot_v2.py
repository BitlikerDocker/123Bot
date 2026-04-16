#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/16 11:28:07
Version: 1.0.0
Description: Telegram Bot 主程序
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


UNSUPPORTED_USER_TEXT = (
    "当前用户({user_id})不支持, "
    "请查看USER_WHITE_LIST变量是否包含当前用户id;详情使用教程请参考{web_site}"
)
WELCOME_TEXT = "欢迎使用 123Bot 快速秒传工具, " "详情使用教程请参考{web_site}"
HELP_TEXT = "详情使用教程请参考{web_site}"
UPLOAD_RUNNING_TEXT = "当前任务正在进行, 已加入后续执行队列"
UPLOAD_STARTED_TEXT = "上传任务已启动, 正在扫描并执行秒传任务"
EMPTY_TEXT = "无"
TOKEN_MISSING_TEXT = "Telegram Bot Token 未配置, " "请检查配置文件或 TG_TOKEN 环境变量"


def _is_user_allowed(user_id: int) -> bool:
    white_list = _config.tg_user_white_list
    if not white_list:
        return True
    return user_id in white_list


def _unsupported_user_text(user_id: int) -> str:
    return UNSUPPORTED_USER_TEXT.format(user_id=user_id, web_site=_config.web_site)


def user_white_list_required(
    handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not user:
            return

        if not _is_user_allowed(user.id):
            if update.effective_message:
                await update.effective_message.reply_text(
                    _unsupported_user_text(user.id)
                )
            return

        await handler(update, context)

    return wrapper


@user_white_list_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.effective_message.reply_text(
        WELCOME_TEXT.format(web_site=_config.web_site)
    )


@user_white_list_required
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await update.effective_message.reply_text(
        HELP_TEXT.format(web_site=_config.web_site)
    )


@user_white_list_required
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    result = await _job_manager.submit_upload_flow()
    if result["queued"]:
        await update.effective_message.reply_text(UPLOAD_RUNNING_TEXT)
        return

    await update.effective_message.reply_text(UPLOAD_STARTED_TEXT)


@user_white_list_required
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    status = await _job_manager.get_status()
    pending_jobs = (
        ",".join(status["pending_jobs"]) if status["pending_jobs"] else EMPTY_TEXT
    )
    current_job = status["current_job"] or EMPTY_TEXT
    last_message = status["last_message"] or EMPTY_TEXT
    message = (
        f"当前任务状态: {status['status']}\n"
        f"当前任务: {current_job}\n"
        f"待执行数量: {status['pending_count']}\n"
        f"待执行任务: {pending_jobs}\n"
        f"最近结果: {last_message}"
    )
    await update.effective_message.reply_text(message)


@user_white_list_required
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.effective_message.document if update.effective_message else None
    if not document or not document.file_name:
        return

    file_name = Path(document.file_name).name
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".json", ".txt"}:
        return

    save_path = Path(_config.json_path) / file_name
    telegram_file = await context.bot.get_file(document.file_id)
    await telegram_file.download_to_drive(custom_path=str(save_path))
    logger.info("Saved telegram file to %s", save_path)

    result = await _job_manager.submit_upload_flow(file_path=str(save_path))
    if result["queued"]:
        reply = (
            f"文件 {file_name} 已保存到 {save_path}, "
            "当前任务正在进行, 已加入后续队列"
        )
    else:
        reply = f"文件 {file_name} 已保存到 {save_path}, " "已开始处理并加入上传任务"
    await update.effective_message.reply_text(reply)


def run_service(token: str):
    """运行 Telegram Bot 服务"""
    if not token:
        raise ValueError(TOKEN_MISSING_TEXT)

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.run_polling()
