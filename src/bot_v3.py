#!/usr/bin/env python
# pylint: disable=E0401,W0718
"""
Author: Bitliker
Date: 2025-11-14 15:51:11
Version: 1.0
Description: tg bot 主程序

"""
import time
import dataclasses
import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config, md_format_html


class Bot:
    """
    tg bot 主程序
    """

    def __init__(self, _cft_: Config) -> None:
        self.cft = _cft_
        self.web_site = "https://example.com"
        self.bot = telebot.TeleBot(_cft_.tg_token, parse_mode=None)
        # 添加 bot 菜单
        self._init_bot_menu(self.bot)
        self._listen_commands(self.bot)
        # self._listen_text(self.bot)
        self.cache_result: dict = {}
        print(f"Bot start...{self.bot.get_my_name().name}")

    def _init_bot_menu(self, _bot: telebot.TeleBot):
        """配置 bot 菜单栏"""
        # 设置键盘命令列表
        commands = [
            telebot.types.BotCommand("start", "开始"),
            telebot.types.BotCommand("help", "帮助"),
            telebot.types.BotCommand("status", "查询服务状态"),
            telebot.types.BotCommand("san", "扫描目录json并执行保存到数据库"),
            telebot.types.BotCommand("upload", "执行秒传"),
            telebot.types.BotCommand("setting", "设置"),
        ]
        _bot.set_my_commands(commands)

    def _listen_commands(self, _bot: telebot.TeleBot):
        """
        监听 指令
        """

        # 帮助指令
        def on_help(message: Message):
            """响应 /help"""
            self._log(f"获取帮助信息:{message.chat.id} || {message.text}")
            if not self._filter_user(message):
                return
            self.bot.reply_to(
                message,
                f"欢迎使用 123Bot 快速秒传工具, 详情使用教程请参考{self.web_site}",
            )

        _bot.message_handler(commands=["help"])(on_help)
        # start 指令暂时跟 help 一样
        self.bot.message_handler(commands=["start"])(on_help)

        # status 指令
        def on_status(message: Message):
            """响应 /status"""
            self._log(f"查询状态:{message.chat.id} || {message.text}")
            if not self._filter_user(message):
                return
            self._handler_status(message)

        self.bot.message_handler(commands=["status"])(on_status)

        # 扫描目录指令
        def on_scan(message: Message):
            """响应 /san"""
            pass

    def _linsten_document(self, _bot: telebot.TeleBot):
        """监听文档文件

        Args:
            _bot (telebot.TeleBot): 机器人内容
        """
        

    def _filter_user(self, message: Message) -> bool:
        """
        过滤用户
        """
        if not self.cft.tg_user_white_list:
            return True
        if message.from_user.id in self.cft.tg_user_white_list:
            self._send_message(
                _chat_id=message.chat.id,
                _text=f"该用户无权限访问, 请配置[{self.cft.tg_user_white_list}]参数",
                msg_id=message.message_id,
            )
            return False
        return True

    def _md_format_html(self, text: str) -> str:
        """将 [Markdown] 转换成 [Html]

        Args:
            text (str): md 格式文本

        Returns:
            str: html 格式文本
        """
        return md_format_html(text)

    def _send_message(self, _chat_id: str, _text: str, msg_id: str = None) -> Message:
        """发送消息"""
        _msg = _text
        _push_ok = False
        _count = 0
        self._log(f"开始推送消息:{_msg}")
        while not _push_ok and _count < 5:
            try:
                message = self.bot.send_message(
                    chat_id=_chat_id,
                    text=_msg,
                    parse_mode="Html",
                    reply_to_message_id=msg_id,
                )
                _push_ok = True
                _count += 1
                return message
            except Exception as e:  # pylint: disable=broad-except
                print(e)
                time.sleep(1)
        return None

    def start_polling(self, skip_pending: bool = True):
        """开始轮询（阻塞），可在服务中调用"""
        try:
            self.bot.infinity_polling(skip_pending=skip_pending)
        except KeyboardInterrupt:
            print("Stopping bot...")

    def _log(self, _message: str):
        """打印日志"""
        print(_message)

    # ***********************************业务区 *****************************
    def _handler_status(self, message: Message):
        """处理状态查询指令"""
        status = self.cache_result.get("status", "未知")
        current_job = self.cache_result.get("current_job", "无")
        pending_jobs = self.cache_result.get("pending_jobs", [])
        last_message = self.cache_result.get("last_message", "无")
        reply = (
            f"当前任务状态: {status}\n"
            f"当前任务: {current_job}\n"
            f"待执行数量: {len(pending_jobs)}\n"
            f"待执行任务: {pending_jobs}\n"
            f"最近结果: {last_message}"
        )
        self._send_message(
            _chat_id=message.chat.id,
            _text=reply,
            msg_id=message.message_id,
        )
