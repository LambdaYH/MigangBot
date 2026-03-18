from __future__ import annotations

import re

_SPACE_RE = re.compile(r"\s+")

_HELP_KEYWORDS = (
    "帮助",
    "help",
    "功能",
    "插件",
    "怎么用",
    "用法",
    "命令",
    "指令",
    "触发",
)

_OVERVIEW_PHRASES = (
    "你会什么",
    "你会干什么",
    "你能干什么",
    "你能做什么",
    "你能干嘛",
    "能用什么",
    "有什么插件",
    "有哪些插件",
    "有什么功能",
    "有哪些功能",
    "插件列表",
    "功能列表",
    "插件总览",
    "功能总览",
    "全部插件",
    "全部功能",
    "所有插件",
    "所有功能",
    "可用插件",
    "可用功能",
)

_OVERVIEW_LEADERS = ("有", "有什么", "有哪些", "会", "会什么", "能", "能用", "都有什么", "都有哪些")
_OVERVIEW_TARGETS = ("插件", "功能", "命令", "指令")


def normalize_help_query(query: str) -> str:
    if not query:
        return ""
    return _SPACE_RE.sub("", query).strip().lower()


def is_help_query(query: str) -> bool:
    normalized = normalize_help_query(query)
    if not normalized:
        return True
    return any(keyword in normalized for keyword in _HELP_KEYWORDS)


def is_help_overview_query(query: str) -> bool:
    normalized = normalize_help_query(query)
    if not normalized:
        return True

    if any(phrase in normalized for phrase in _OVERVIEW_PHRASES):
        return True

    if any(target in normalized for target in _OVERVIEW_TARGETS):
        if any(leader in normalized for leader in _OVERVIEW_LEADERS):
            return True
        if any(word in normalized for word in ("列表", "总览", "大全", "汇总", "介绍")):
            return True

    return False
