from __future__ import annotations

_GENERAL_IMAGE_HINTS = (
    "看图",
    "看下图",
    "看看图",
    "这张图",
    "这个图",
    "图片",
    "照片",
    "截图",
    "看得懂",
    "看懂",
    "这是什么",
    "图里",
    "图上",
    "帮我看看",
)

_IMAGE_TOOL_HINTS = (
    "二维码",
    "扫码",
    "ocr",
    "识别文字",
    "提取文字",
    "翻译图片",
    "识图",
    "搜图",
    "以图搜图",
)


def is_explicit_image_tool_query(query: str) -> bool:
    normalized = str(query or "").strip().lower()
    return any(keyword in normalized for keyword in _IMAGE_TOOL_HINTS)


def is_general_image_understanding_query(query: str) -> bool:
    normalized = str(query or "").strip().lower()
    if not normalized:
        return False
    if is_explicit_image_tool_query(normalized):
        return False
    return any(keyword in normalized for keyword in _GENERAL_IMAGE_HINTS)
