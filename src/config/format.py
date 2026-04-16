#!/usr/bin/env python

"""
Author: Bitliker
Date: 2025-07-15 10:06:09
Version: 1.0
Description: 通用组件

"""
import re


def url_code(_url: str) -> str:
    """URL编码解码"""
    return _url.replace("%", "\\%").replace("&", "&amp;")


def remove_special_characters(_title: str) -> str:
    """去除特殊字符"""
    return re.sub(r'[\\/*?:"<>|]', "", _title).strip()


def md_format_html(text: str) -> str:
    """将 [Markdown] 转换成 [Html]

    Args:
        text (str): md 格式文本

    Returns:
        str: html 格式文本
    """
    if not text:
        return ""

    # 先对全部文本做 HTML 转义，保护用户输入
    escaped = html.escape(text)

    # 处理多行代码块 ```...```
    def _repl_codeblock(m):
        inner = m.group(1)
        return f"<pre><code>{inner}</code></pre>"

    escaped = re.sub(r"```([\s\S]*?)```", _repl_codeblock, escaped)

    # 处理行内代码 `...`
    escaped = re.sub(r"`([^`\n]+)`", lambda m: f"<code>{m.group(1)}</code>", escaped)

    # 处理链接 [text](url)
    def _repl_link(m):
        txt = m.group(1)
        url = m.group(2)
        return f'<a href="{html.escape(url, quote=True)}">{txt}</a>'

    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _repl_link, escaped)

    # 处理粗体 **text** 和 __text__
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"__(.+?)__", r"<b>\1</b>", escaped)

    # 处理斜体 *text* 和 _text_（避免与粗体冲突）
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<i>\1</i>", escaped)

    return escaped.replace("|", "&#124;")
