#!/usr/bin/env python
# pylint: disable=E0401,W0718
"""
Author: Bitliker
Date: 2025-11-14 15:51:11
Version: 1.0
Description: tg bot 主程序

"""
import os
import time
import dataclasses
import threading
from pathlib import Path
import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config, md_format_html
from job2 import JobManager, JobType


class Bot:
    """
    tg bot 主程序
    """

    def __init__(self, _cft_: Config) -> None:
        self.cft = _cft_
        self.web_site = getattr(_cft_, "web_site", "https://example.com")
        self.bot = telebot.TeleBot(_cft_.tg_token, parse_mode=None)

        # 任务管理器（单例）
        self._job_manager = JobManager()

        # 并发控制 - 文件操作锁
        self._file_lock = threading.Lock()

        # 设置命令的状态管理 {user_id: setting_key}
        self._setting_state = {}

        # 添加 bot 菜单
        self._init_bot_menu(self.bot)
        self._listen_commands(self.bot)
        self._linsten_document(self.bot)
        self._listen_setting_input(self.bot)
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
            """响应 /san - 扫描目录json并执行保存到数据库"""
            self._log(f"扫描目录:{message.chat.id} || {message.text}")
            if not self._filter_user(message):
                return

            if self._job_manager.is_running():
                self._send_message(
                    _chat_id=message.chat.id,
                    _text="当前任务正在进行中，请稍候...",
                    msg_id=message.message_id,
                )
                return

            # 提交扫描任务
            if self._job_manager.submit_job(JobType.UPLOAD_BY_DB, limit=10):
                self._send_message(
                    _chat_id=message.chat.id,
                    _text="扫描任务已启动，正在处理...",
                    msg_id=message.message_id,
                )
                # 在后台线程中执行任务
                threading.Thread(
                    target=self._execute_job_in_background, args=(message.chat.id,)
                ).start()
            else:
                self._send_message(
                    _chat_id=message.chat.id,
                    _text="当前有任务进行中，扫描任务已加入队列",
                    msg_id=message.message_id,
                )

        self.bot.message_handler(commands=["san"])(on_scan)

        # 上传指令
        def on_upload(message: Message):
            """响应 /upload - 执行秒传"""
            self._log(f"执行上传:{message.chat.id} || {message.text}")
            if not self._filter_user(message):
                return

            if self._job_manager.is_running():
                self._send_message(
                    _chat_id=message.chat.id,
                    _text="当前任务正在进行中，请稍候...",
                    msg_id=message.message_id,
                )
                return

            # 提交上传任务
            if self._job_manager.submit_job(JobType.UPLOAD_BY_DB, limit=10):
                self._send_message(
                    _chat_id=message.chat.id,
                    _text="上传任务已启动...",
                    msg_id=message.message_id,
                )
                # 在后台线程中执行任务
                threading.Thread(
                    target=self._execute_job_in_background, args=(message.chat.id,)
                ).start()
            else:
                self._send_message(
                    _chat_id=message.chat.id,
                    _text="当前有任务进行中，上传任务已加入队列",
                    msg_id=message.message_id,
                )

        self.bot.message_handler(commands=["upload"])(on_upload)

        # 设置指令
        def on_setting(message: Message):
            """响应 /setting - 设置配置"""
            self._log(f"打开设置:{message.chat.id} || {message.text}")
            if not self._filter_user(message):
                return

            # 显示设置菜单
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(
                    "设置 p123_username", callback_data="set_p123_username"
                ),
                InlineKeyboardButton(
                    "设置 p123_password", callback_data="set_p123_password"
                ),
            )
            markup.add(
                InlineKeyboardButton("设置 p123_token", callback_data="set_p123_token"),
                InlineKeyboardButton(
                    "设置 tg_user_white_list", callback_data="set_tg_user_white_list"
                ),
            )
            markup.add(
                InlineKeyboardButton(
                    "设置 is_auto_upload", callback_data="set_is_auto_upload"
                ),
            )

            self._send_message(
                _chat_id=message.chat.id,
                _text="请选择要设置的配置项:",
                msg_id=message.message_id,
            )
            self.bot.send_message(
                chat_id=message.chat.id,
                text="选择要修改的配置:",
                reply_markup=markup,
            )

        self.bot.message_handler(commands=["setting"])(on_setting)

        # 处理回调查询（设置菜单选择）
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
        def handle_setting_callback(call: telebot.types.CallbackQuery):
            """处理设置菜单的回调"""
            user_id = call.from_user.id
            setting_key = call.data[4:]  # 去掉 "set_" 前缀

            self._setting_state[user_id] = setting_key

            # 提示信息
            prompt_map = {
                "p123_username": "请输入 p123_username (123盘手机号码):",
                "p123_password": "请输入 p123_password (123盘密码):",
                "p123_token": "请输入 p123_token:",
                "tg_user_white_list": f"当前白名单: {self.cft.tg_user_white_list}\n请输入新的白名单 (逗号分隔的用户ID):",
                "is_auto_upload": "请输入 is_auto_upload (true 或 false):",
            }

            prompt = prompt_map.get(setting_key, "请输入新值:")

            self.bot.send_message(chat_id=call.message.chat.id, text=prompt)
            self.bot.answer_callback_query(call.id)

    def _linsten_document(self, _bot: telebot.TeleBot):
        """监听文档文件

        Args:
            _bot (telebot.TeleBot): 机器人内容
        """

        def on_document(message: Message):
            """处理文档文件消息"""
            self._log(f"接收文件:{message.chat.id} || {message.document.file_name}")

            # 检查用户权限
            if not self._filter_user(message):
                return

            # 获取文件信息
            file_name = message.document.file_name
            file_extension = os.path.splitext(file_name)[1].lower()

            # 检查文件类型
            if file_extension not in [".json", ".txt"]:
                self._send_message(
                    _chat_id=message.chat.id,
                    _text=f"不支持的文件类型: {file_extension}，仅支持 .json 和 .txt 文件",
                    msg_id=message.message_id,
                )
                return

            try:
                # 线程安全的文件操作
                with self._file_lock:
                    # 下载文件
                    file_info = _bot.get_file(message.document.file_id)
                    downloaded_file = _bot.download_file(file_info.file_path)

                    # 生成带时间戳的文件名防止重复
                    timestamp = int(time.time() * 1000000)
                    base_name, ext = os.path.splitext(file_name)
                    unique_file_name = f"{base_name}_{timestamp}{ext}"
                    save_path = os.path.join(self.cft.json_path, unique_file_name)

                    # 使用 JobManager 的方法保存文件
                    ok, save_msg = self._job_manager.save_file(
                        save_path, downloaded_file
                    )

                if not ok:
                    self._send_message(
                        _chat_id=message.chat.id,
                        _text=save_msg,
                        msg_id=message.message_id,
                    )
                    return

                self._log(f"文件已保存: {save_path}")

                # 根据 is_auto_upload 判断是否自动上传
                if self.cft.is_auto_upload:
                    # 自动上传模式：直接启动上传任务
                    if self._job_manager.submit_job(JobType.UPLOAD_BY_DB, limit=10):
                        # 立即执行
                        self._send_message(
                            _chat_id=message.chat.id,
                            _text=f"文件 {file_name} 已接收，自动上传模式启用，处理中...",
                            msg_id=message.message_id,
                        )
                        # 在后台线程中执行任务
                        threading.Thread(
                            target=self._execute_job_in_background, args=(message.chat.id,)
                        ).start()
                    else:
                        # 添加到队列
                        self._send_message(
                            _chat_id=message.chat.id,
                            _text=f"文件 {file_name} 已接收，自动上传已加入队列",
                            msg_id=message.message_id,
                        )
                else:
                    # 手动模式：启动 json_to_db 任务
                    # 提交 json_to_db 任务
                    if self._job_manager.submit_job(
                        JobType.JSON_TO_DB, file_path=save_path
                    ):
                        # 立即执行
                        self._send_message(
                            _chat_id=message.chat.id,
                            _text=f"文件 {file_name} 已接收，处理中...",
                            msg_id=message.message_id,
                        )
                        # 在后台线程中执行任务
                        threading.Thread(
                            target=self._execute_job_in_background, args=(message.chat.id,)
                        ).start()
                    else:
                        # 添加到队列
                        self._send_message(
                            _chat_id=message.chat.id,
                            _text=f"文件 {file_name} 已接收，当前有任务进行中，将队列等待处理",
                            msg_id=message.message_id,
                        )

            except Exception as e:  # pylint: disable=broad-except
                error_msg = f"文件下载失败: {str(e)}"
                self._log(error_msg)
                self._send_message(
                    _chat_id=message.chat.id,
                    _text=error_msg,
                    msg_id=message.message_id,
                )

        # 注册文档处理器
        _bot.message_handler(content_types=["document"])(on_document)

    def _handle_setting_input(self, message: Message):
        """处理设置命令的文本输入"""
        user_id = message.from_user.id

        if user_id not in self._setting_state:
            return

        setting_key = self._setting_state[user_id]
        user_input = message.text.strip()

        try:
            if setting_key == "p123_username":
                self.cft.p123_username = user_input
                response_msg = f"✅ p123_username 已更新为: {user_input}"

            elif setting_key == "p123_password":
                self.cft.p123_password = user_input
                response_msg = "✅ p123_password 已更新"

            elif setting_key == "p123_token":
                self.cft.p123_token = user_input
                response_msg = "✅ p123_token 已更新"

            elif setting_key == "tg_user_white_list":
                # 解析逗号分隔的用户ID
                user_ids = [int(x.strip()) for x in user_input.split(",") if x.strip()]
                self.cft.tg_user_white_list = user_ids
                response_msg = f"✅ tg_user_white_list 已更新为: {user_ids}"

            elif setting_key == "is_auto_upload":
                # 解析布尔值
                value = user_input.lower() in ["true", "1", "yes", "是"]
                self.cft.is_auto_upload = value
                response_msg = f"✅ is_auto_upload 已更新为: {value}"

            else:
                response_msg = "❌ 未知的设置项"

            # 保存配置到文件
            config_path = os.path.join(self.cft.media_path, "config", "config.json")
            self.cft.save_to_file(config_path)

            # 清除设置状态
            del self._setting_state[user_id]

            # 发送成功消息
            self._send_message(
                _chat_id=message.chat.id,
                _text=response_msg,
                msg_id=message.message_id,
            )

        except ValueError:
            error_msg = "❌ 输入格式错误，请重试"
            self._send_message(
                _chat_id=message.chat.id,
                _text=error_msg,
                msg_id=message.message_id,
            )
            # 清除设置状态
            del self._setting_state[user_id]

        except Exception as e:  # pylint: disable=broad-except
            self._log(f"设置保存失败: {e}")
            error_msg = f"❌ 设置保存失败: {str(e)}"
            self._send_message(
                _chat_id=message.chat.id,
                _text=error_msg,
                msg_id=message.message_id,
            )
            del self._setting_state[user_id]

    def _listen_setting_input(self, _bot: telebot.TeleBot):
        """监听设置输入的文本消息"""

        def on_text_message(message: Message):
            """处理文本消息"""
            user_id = message.from_user.id

            # 只处理处于设置状态的用户消息
            if user_id in self._setting_state:
                self._handle_setting_input(message)

        # 注册文本消息处理器
        _bot.message_handler(func=lambda message: True)(on_text_message)

    def _filter_user(self, message: Message) -> bool:
        """
        过滤用户 - 检查用户是否在白名单中
        """
        # 如果白名单为空，允许所有用户
        if not self.cft.tg_user_white_list:
            return True

        # 检查用户ID是否在白名单中
        if message.from_user.id not in self.cft.tg_user_white_list:
            self._send_message(
                _chat_id=message.chat.id,
                _text=f"当前用户({message.from_user.id})不支持, 请查看USER_WHITE_LIST变量是否包含当前用户id;详情使用教程请参考{self.web_site}",
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
    def _execute_job_in_background(self, chat_id: int):
        """在后台线程中执行任务"""
        try:
            # 执行当前任务
            success, message = self._job_manager.execute_current_job()

            # 发送执行结果
            if success:
                self._send_message(
                    _chat_id=chat_id,
                    _text=f"✅ 任务完成: {message}",
                )
            else:
                self._send_message(
                    _chat_id=chat_id,
                    _text=f"❌ 任务失败: {message}",
                )

            # 完成任务，检查是否有待执行任务
            next_job = self._job_manager.finish_current_job(success, message)

            # 如果有待执行任务，继续执行
            if next_job:
                self._log(f"执行待执行任务: {next_job.task_type.value}")
                self._execute_job_in_background(chat_id)

        except Exception as e:  # pylint: disable=broad-except
            self._log(f"后台任务执行异常: {e}")
            self._send_message(
                _chat_id=chat_id,
                _text=f"❌ 任务执行异常: {str(e)}",
            )
            self._job_manager.finish_current_job(False, str(e))

    def _handler_status(self, message: Message):
        """处理状态查询指令"""
        status_info = self._job_manager.get_status()

        status_text = f"当前任务状态: {status_info['status']}\n"

        if status_info["current_job"]:
            current_job = status_info["current_job"]
            status_text += f"当前任务: {current_job['type']}\n"
        else:
            status_text += "当前任务: 无\n"

        if status_info["pending_count"] > 0:
            status_text += f"待执行数量: {status_info['pending_count']}\n"
            pending_types = ", ".join([j["type"] for j in status_info["pending_jobs"]])
            status_text += f"待执行任务: {pending_types}\n"
        else:
            status_text += "待执行数量: 0\n"
            status_text += "待执行任务: 无\n"

        self._send_message(
            _chat_id=message.chat.id,
            _text=status_text,
            msg_id=message.message_id,
        )
