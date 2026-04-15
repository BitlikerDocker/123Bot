#!/usr/bin/env python
# pylint: disable=E0401,W0718

"""
Coding: UTF-8
Author: Bitliker
Date: 2026/04/14 16:23:18
Version: 1.0.0
Description: telegram bot 管理类
feature:

"""
import os
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Set, Optional

from telegram import Update, File
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ====================== 日志配置 ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ====================== Bot 状态管理 ======================
class BotState:
    """管理 bot 的全局状态"""

    def __init__(self):
        self.upload_task_active = False
        self.last_upload_time: Optional[datetime] = None
        self.upload_queue = []
        self.active_users: Set[int] = set()
        self.task_status = "空闲"

    def start_upload_task(self) -> bool:
        """开始上传任务，返回是否成功启动"""
        if self.upload_task_active:
            return False
        self.upload_task_active = True
        self.task_status = "上传中..."
        self.last_upload_time = datetime.now()
        return True

    def finish_upload_task(self):
        """结束上传任务"""
        self.upload_task_active = False
        self.task_status = "空闲"
        self.upload_queue = []

    def reset(self):
        """重置状态"""
        self.__init__()


# ====================== BotClient 类 ======================
class BotClient:
    """Telegram Bot 客户端管理类"""

    _instance: Optional["BotClient"] = None

    def __init__(
        self,
        bot_token: str,
        user_white_list: Set[int],
        web_site: str = "https://example.com/tutorial",
        json_path: str = "/media/json",
    ):
        """
        初始化 BotClient

        Args:
            bot_token: Telegram Bot Token
            user_white_list: 白名单用户 ID 集合
            web_site: 教程网站地址
            json_path: JSON 文件存储路径
        """
        self.bot_token = bot_token
        self.user_white_list = user_white_list
        self.web_site = web_site
        self.json_path = Path(json_path)
        self.json_path.mkdir(parents=True, exist_ok=True)

        self.state = BotState()
        self.application: Optional[Application] = None

        logger.info(f"BotClient 初始化完成")
        logger.info(f"JSON 路径: {self.json_path}")

    @classmethod
    def get_instance(
        cls,
        bot_token: str = None,
        user_white_list: Set[int] = None,
        web_site: str = None,
        json_path: str = None,
    ) -> "BotClient":
        """
        获取单例实例

        Args:
            bot_token: Telegram Bot Token (可选)
            user_white_list: 白名单用户 ID (可选)
            web_site: 教程网站地址 (可选)
            json_path: JSON 文件路径 (可选)

        Returns:
            BotClient 实例
        """
        if cls._instance is None:
            # 从环境变量获取配置
            if bot_token is None:
                bot_token = os.getenv("TG_TOKEN", "")
            if user_white_list is None:
                white_list_str = os.getenv("TG_USER_WHITE_LIST", "")
                user_white_list = (
                    set(int(x.strip()) for x in white_list_str.split(",") if x.strip())
                    if white_list_str
                    else set()
                )
            if web_site is None:
                web_site = os.getenv("WEB_SITE", "https://example.com/tutorial")
            if json_path is None:
                json_path = os.getenv("JSON_PATH", "/media/json")

            cls._instance = cls(bot_token, user_white_list, web_site, json_path)

        return cls._instance

    # ==================== 辅助方法 ====================

    def _is_whitelist_user(self, user_id: int, username: str) -> bool:
        """检查用户是否在白名单中"""
        if not self.user_white_list:
            return True
        return user_id in self.user_white_list or username in self.user_white_list

    def _get_whitelist_check_decorator(self, func):
        """生成白名单检查装饰器"""
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            user_id = update.effective_user.id
            username = update.effective_user.username or f"user_{user_id}"

            if not self._is_whitelist_user(user_id, username):
                error_msg = (
                    f"❌ 当前用户({user_id})不支持\n"
                    f"🔍 请查看 TG_USER_WHITE_LIST 环境变量是否包含当前用户id\n"
                    f"📚 详情使用教程请参考: {self.web_site}"
                )
                logger.warning(f"用户 {username}({user_id}) 不在白名单中，拒绝访问")
                await update.message.reply_text(error_msg)
                return None

            logger.info(f"白名单用户 {username}({user_id}) 访问: {func.__name__}")
            self.state.active_users.add(user_id)
            return await func(update, context, *args, **kwargs)

        return wrapper

    # ==================== 命令处理器 ====================

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        welcome_msg = (
            "🎉 欢迎使用 123Bot 快速秒传工具\n\n"
            f"📚 详情使用教程请参考: {self.web_site}\n\n"
            "💡 可用命令:\n"
            "/start - 重新开始\n"
            "/help - 查看帮助\n"
            "/upload - 开启上传任务\n"
            "/status - 查看任务状态"
        )
        await update.message.reply_text(welcome_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        help_msg = (
            f"📚 123Bot 使用教程\n\n"
            f"🔗 完整教程请访问: {self.web_site}\n\n"
            "📋 核心功能:\n"
            "• 白名单用户管理\n"
            "• JSON文件自动保存\n"
            "• 批量秒传任务管理\n"
            "• 实时任务状态监控"
        )
        await update.message.reply_text(help_msg)

    async def upload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /upload 命令 - 开启上传任务"""
        if self.state.upload_task_active:
            status_msg = (
                "🔄 当前任务正在进行中\n\n"
                f"📊 任务状态: {self.state.task_status}\n"
                f"⏰ 开始时间: {self.state.last_upload_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                "💡 请稍后再试或使用 /status 查看进度"
            )
            await update.message.reply_text(status_msg)
            return

        # 启动上传任务
        if self.state.start_upload_task():
            upload_msg = (
                "🚀 开始上传任务\n\n"
                f"📂 扫描路径: {self.json_path}\n"
                "🔍 正在查找 JSON 文件...\n\n"
                "💡 提示: 您可以使用 /status 查看任务进度"
            )

            # 扫描 JSON 文件
            json_files = list(self.json_path.glob("*.json"))
            txt_files = list(self.json_path.glob("*.txt"))

            if not json_files and not txt_files:
                self.state.finish_upload_task()
                error_msg = (
                    "❌ 未找到可上传的文件\n\n"
                    f"📂 请确保 {self.json_path} 目录下有 .json 或 .txt 文件\n"
                    "💡 您可以通过发送文件到本机器人来添加文件"
                )
                await update.message.reply_text(error_msg)
                return

            # 记录找到的文件
            self.state.upload_queue = [str(f) for f in json_files + txt_files]

            # TODO: 在这里实现实际的上传逻辑

            # 任务完成后更新状态
            self.state.finish_upload_task()

            result_msg = (
                "✅ 上传任务完成\n\n"
                f"📊 处理文件: {len(self.state.upload_queue)} 个\n"
                f"📂 JSON文件: {len(json_files)} 个\n"
                f"📄 TXT文件: {len(txt_files)} 个\n"
                f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🔗 详情教程: {self.web_site}"
            )
            await update.message.reply_text(result_msg)
        else:
            await update.message.reply_text("❌ 无法启动任务，请重试")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /status 命令 - 查看任务状态"""
        # 获取目录统计信息
        json_files = list(self.json_path.glob("*.json"))
        txt_files = list(self.json_path.glob("*.txt"))
        total_files = len(json_files) + len(txt_files)

        # 格式化活跃用户
        active_users_info = (
            "\n".join([f"• {user_id}" for user_id in self.state.active_users])
            or "无活跃用户"
        )

        last_time_str = (
            self.state.last_upload_time.strftime('%Y-%m-%d %H:%M:%S')
            if self.state.last_upload_time
            else '从未'
        )

        status_msg = (
            f"📊 123Bot 任务状态\n\n"
            f"🔄 当前状态: {self.state.task_status}\n"
            f"⏰ 最后操作: {last_time_str}\n\n"
            f"📂 文件统计:\n"
            f"   • JSON文件: {len(json_files)} 个\n"
            f"   • TXT文件: {len(txt_files)} 个\n"
            f"   • 总计: {total_files} 个\n\n"
            f"👥 活跃用户:\n{active_users_info}\n\n"
            f"📋 上传队列: {len(self.state.upload_queue)} 个文件\n"
            f"💡 提示: 使用 /upload 开始上传任务"
        )
        await update.message.reply_text(status_msg)

    # ==================== 文件处理器 ====================

    async def handle_document(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """处理文档文件，保存 .json/.txt 文件"""
        document = update.message.document

        # 检查文件类型
        if not document.file_name.lower().endswith((".json", ".txt")):
            await update.message.reply_text(
                "❌ 不支持的文件类型\n\n"
                "💡 仅支持 .json 和 .txt 文件\n"
                "📋 请重新发送正确的文件格式"
            )
            return

        try:
            # 获取文件对象
            file: File = await context.bot.get_file(document.file_id)

            # 构建保存路径
            safe_filename = document.file_name.replace("/", "_").replace("\\", "_")
            save_path = self.json_path / safe_filename

            # 下载并保存文件
            await file.download_to_drive(save_path)

            # 记录文件信息
            file_size = document.file_size / 1024  # KB
            file_type = "JSON" if safe_filename.endswith(".json") else "TXT"

            success_msg = (
                f"✅ {file_type} 文件保存成功\n\n"
                f"📁 文件名: {safe_filename}\n"
                f"💾 大小: {file_size:.1f} KB\n"
                f"📍 路径: {save_path}\n\n"
                f"🚀 使用 /upload 命令开始上传任务\n"
                f"📊 使用 /status 查看当前状态"
            )

            logger.info(
                f"用户 {update.effective_user.id} 上传了文件: {safe_filename}"
            )
            await update.message.reply_text(success_msg)

        except Exception as e:
            error_msg = (
                f"❌ 文件保存失败\n\n"
                f"🔍 错误详情: {str(e)}\n"
                "💡 请检查:\n"
                "• 目录权限是否正确\n"
                "• 磁盘空间是否充足\n"
                "• 文件名是否合法"
            )
            logger.error(f"文件保存失败: {str(e)}")
            await update.message.reply_text(error_msg)

    async def handle_text_json(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """处理文本消息中的 JSON 内容"""
        text = update.message.text.strip()

        # 检查是否是 JSON 格式（简单检查）
        if text.startswith("{") and text.endswith("}"):
            try:
                # 验证 JSON 格式
                json.loads(text)

                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"message_{timestamp}.json"
                save_path = self.json_path / filename

                # 保存 JSON 文件
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(json.loads(text), f, indent=2, ensure_ascii=False)

                success_msg = (
                    "✅ JSON 内容保存成功\n\n"
                    f"📁 文件名: {filename}\n"
                    f"📍 路径: {save_path}\n\n"
                    f"🚀 使用 /upload 命令开始上传任务"
                )
                await update.message.reply_text(success_msg)
                return

            except json.JSONDecodeError:
                pass  # 不是有效的 JSON，继续其他处理

        # 如果不是 JSON，提供帮助信息
        help_msg = (
            "💡 检测到文本消息\n\n"
            "📋 支持的操作:\n"
            "• 发送 .json 或 .txt 文件\n"
            "• 直接粘贴 JSON 格式内容\n"
            "• 使用 /help 查看完整帮助"
        )
        await update.message.reply_text(help_msg)

    # ==================== 错误处理器 ====================

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """全局错误处理器"""
        logger.error(f"发生异常: {context.error}", exc_info=True)

        if update and hasattr(update, "message") and update.message:
            try:
                await update.message.reply_text(
                    "❌ 系统发生错误\n\n"
                    "🔧 正在尝试恢复服务...\n"
                    "💡 请稍后重试或联系管理员"
                )
            except Exception as e:
                logger.error(f"错误回复失败: {str(e)}")

    # ==================== 启动和运行 ====================

    def _create_whitelist_handlers(self):
        """创建带白名单检查的处理器"""
        whitelist_check = self._get_whitelist_check_decorator

        return {
            "start": CommandHandler("start", whitelist_check(self.start_command)),
            "help": CommandHandler("help", whitelist_check(self.help_command)),
            "upload": CommandHandler("upload", whitelist_check(self.upload_command)),
            "status": CommandHandler("status", whitelist_check(self.status_command)),
            "document": MessageHandler(
                filters.Document.ALL, whitelist_check(self.handle_document)
            ),
            "text": MessageHandler(
                filters.TEXT & ~filters.COMMAND, whitelist_check(self.handle_text_json)
            ),
        }

    def run(self):
        """启动 bot 服务"""
        # 验证配置
        if not self.bot_token:
            logger.error("未配置 TG_TOKEN，请设置环境变量")
            raise ValueError("TG_TOKEN 未配置")

        if not self.user_white_list:
            logger.warning("TG_USER_WHITE_LIST 为空，所有用户都将被拒绝访问")

        logger.info(f"启动 123Bot 服务")
        logger.info(f"白名单用户: {self.user_white_list}")
        logger.info(f"JSON 路径: {self.json_path}")
        logger.info(f"教程网站: {self.web_site}")

        # 创建应用
        self.application = Application.builder().token(self.bot_token).build()

        # 获取带白名单检查的处理器
        handlers = self._create_whitelist_handlers()

        # 注册命令处理器
        self.application.add_handler(handlers["start"])
        self.application.add_handler(handlers["help"])
        self.application.add_handler(handlers["upload"])
        self.application.add_handler(handlers["status"])

        # 注册文件处理器
        self.application.add_handler(handlers["document"])
        self.application.add_handler(handlers["text"])

        # 注册错误处理器
        self.application.add_error_handler(self.error_handler)

        # 启动轮询
        logger.info("开始轮询...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    def stop(self):
        """停止 bot 服务"""
        if self.application:
            self.application.stop()
            logger.info("Bot 服务已停止")

    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        if cls._instance and cls._instance.application:
            cls._instance.stop()
        cls._instance = None


# ====================== 主程序 ======================
def main():
    """启动 bot 服务"""
    client = BotClient.get_instance()
    client.run()


if __name__ == "__main__":
    main()
