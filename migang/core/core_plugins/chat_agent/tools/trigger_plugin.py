import re

from nonebot.log import logger
from nonebot.matcher import current_bot, current_event
from nonebot.adapters.onebot.v11 import Message, MessageSegment, GroupMessageEvent

from migang.core.utils.langchain_tool import nb_langchain_tool
from migang.core.core_plugins.help.data_source import get_plugin_help

from ..plugin_index import plugin_index
from ..plugin_reranker import plugin_reranker
from ..help_intent import normalize_help_query, is_help_overview_query

_LLM_BLOCKED_PLUGIN_NAMES = {"dismiss", "switch_bot"}
_LLM_BLOCKED_COMMAND_PREFIXES = (".dismiss",)
_LLM_BLOCKED_FULLMATCH_COMMANDS = ("起床啦", "醒来吧", "醒来", "起床", "休息吧", "睡吧")
_INLINE_URL_RE = re.compile(r"(?:https?|file)://\S+")


def _blocked_plugin_reason(plugin_name: str) -> str | None:
    if plugin_name in _LLM_BLOCKED_PLUGIN_NAMES:
        return f"插件 {plugin_name} 已禁止由 LLM 自动调用。"
    return None


def _blocked_command_reason(content: str) -> str | None:
    normalized = str(content or "").strip()
    if not normalized:
        return None
    if normalized.startswith(_LLM_BLOCKED_COMMAND_PREFIXES):
        return "该指令已禁止由 LLM 自动调用。"
    if normalized in _LLM_BLOCKED_FULLMATCH_COMMANDS:
        return "该指令已禁止由 LLM 自动调用。"
    return None


def _collect_current_images(event) -> Message:
    if not event or not getattr(event, "message", None):
        return Message()
    image_message = Message()
    for seg in event.message:
        if seg.type == "image":
            image_message.append(seg)
    return image_message


def _collect_current_image_urls(event) -> set[str]:
    if not event or not getattr(event, "message", None):
        return set()
    urls: set[str] = set()
    for seg in event.message:
        if seg.type != "image":
            continue
        for key in ("url", "file"):
            value = str(seg.data.get(key) or "").strip()
            if value and "://" in value:
                urls.add(value)
    return urls


def _sanitize_command_for_attached_images(
    content: str,
    fallback_command: str = "",
    removable_urls: set[str] | None = None,
) -> str:
    removable_urls = removable_urls or set()

    def replace_url(match: re.Match[str]) -> str:
        url = match.group(0)
        return "" if url in removable_urls else url

    sanitized = _INLINE_URL_RE.sub(replace_url, str(content or ""))
    sanitized = sanitized.replace("[图片]", " ")
    sanitized = " ".join(sanitized.split()).strip()
    if sanitized:
        return sanitized
    return fallback_command.strip() or str(content or "").strip()


async def _dispatch_plugin_command(
    content: str,
    attach_current_images: bool = False,
) -> str:
    if not content:
        return "请输入插件指令"
    if blocked_reason := _blocked_command_reason(content):
        return blocked_reason
    bot = current_bot.get()
    event = current_event.get()
    if not bot or not event:
        return "无法获取当前bot或event，无法触发插件。"
    image_message = Message()
    if attach_current_images:
        image_message = _collect_current_images(event)
    image_count = sum(1 for seg in image_message if seg.type == "image")
    logger.info(
        f"触发插件: {content}"
        + (f" | 携带当前消息图片={image_count}" if attach_current_images else "")
    )
    if isinstance(event, GroupMessageEvent):
        at_msg = MessageSegment.at(event.self_id) + Message(content)
    else:
        at_msg = Message(content)
    if image_count:
        at_msg += MessageSegment.text(" ")
        at_msg += image_message
    new_event = event.model_copy()
    new_event.message = at_msg
    new_event.original_message = at_msg
    new_event.raw_message = str(at_msg)
    setattr(new_event, "llm_trigger", True)
    try:
        await bot.handle_event(new_event)
        return "插件已触发，结果已直接发送给用户"
    except Exception as e:
        return f"插件触发失败: {e}"


@nb_langchain_tool
async def trigger_plugin(content: str, attach_current_images: bool = False):
    """
    触发插件，通过输入指令实现插件的触发

    Args:
        content (str): 触发插件的完整指令
        attach_current_images (bool): 是否附带当前用户消息中的图片，用于需要图片输入的插件
    """
    return await _dispatch_plugin_command(
        content, attach_current_images=attach_current_images
    )


@nb_langchain_tool
async def query_help_plugin(query: str = "") -> str:
    """
    通过 help 插件体系查询帮助信息。
    适用于这类问题：有哪些功能、有哪些插件、某个插件怎么用、某个命令怎么触发。

    Args:
        query (str): 为空时返回当前会话的功能概览；不为空时返回最相关插件的帮助
    """
    normalized = normalize_help_query(query)
    if is_help_overview_query(normalized):
        return await _dispatch_plugin_command("帮助")

    entry = plugin_index.resolve(normalized)
    if entry:
        direct_help_result = await _dispatch_plugin_command(f"帮助 {entry.display_name}")
        if "插件已触发" in direct_help_result:
            return direct_help_result
        help_text = get_plugin_help(normalized) or get_plugin_help(entry.plugin_name)
        detail = plugin_index.render_plugin_detail(
            entry.plugin_name, event=current_event.get(None)
        )
        if help_text:
            return f"{detail}\n用法说明: {help_text}"
        return detail

    visible_entries = {
        entry.plugin_name
        for entry in plugin_index.user_visible_entries(current_event.get(None))
    }
    candidates = [
        entry
        for entry in plugin_index.search(
            normalized, limit=10, event=current_event.get(None)
        )
        if entry.plugin_name in visible_entries
    ][:5]
    if not candidates:
        return f"没有找到和“{normalized}”相关的帮助信息。"

    lines = [f"和“{normalized}”最相关的帮助项："]
    for index, entry in enumerate(candidates, start=1):
        help_text = get_plugin_help(entry.plugin_name) or ""
        availability = plugin_index.get_availability(
            entry.plugin_name, current_event.get(None)
        )
        line = f"{index}. {entry.short_label()} | 状态: {availability.status_text}"
        if entry.commands:
            line += " | 示例: " + " / ".join(
                command.example for command in entry.preferred_commands(limit=2)
            )
        lines.append(line)
        if help_text:
            lines.append(
                f"   用法: {help_text[:160]}{'...' if len(help_text) > 160 else ''}"
            )
    return "\n".join(lines)


@nb_langchain_tool
async def search_project_plugins(query: str, limit: int = 5) -> str:
    """
    为执行任务检索当前工程中的插件，返回最相关插件的名称、推荐触发词和状态。
    不适用于“有哪些功能/某插件怎么用”这类帮助问题；帮助问题应优先调用 query_help_plugin。
    也不适用于“帮我看看这张图/图里有什么/你看得懂吗”这类通用看图问题；这类问题应先直接基于图片回答，
    只有明确需要二维码、OCR、提取文字、翻译图片等工具时，才检索插件。
    如果当前用户消息已经带了插件需要处理的图片，在选定插件后，应继续调用 invoke_project_plugin，
    不要要求用户再次发送图片。

    Args:
        query (str): 用户需求描述
        limit (int): 返回结果数量，默认 5
    """
    event = current_event.get(None)
    limit = max(1, min(limit, 8))
    visible_plugin_names = {
        entry.plugin_name for entry in plugin_index.user_visible_entries(event)
    }
    matches = [
        match
        for match in plugin_index.search_matches(
            query, limit=max(limit * 3, 8), event=event
        )
        if match.entry.plugin_name in visible_plugin_names
    ]
    if plugin_reranker.should_rerank(query, matches):
        candidate_summary = ", ".join(
            f"{match.entry.plugin_name}({match.score:.1f})" for match in matches[:4]
        )
        logger.info(f"触发插件检索 LLM 重排: query={query} | candidates={candidate_summary}")
        matches = await plugin_reranker.rerank(query, matches)
    return plugin_index.render_match_results(
        query=query, matches=matches[:limit], event=event
    )


@nb_langchain_tool
def inspect_project_plugin(plugin_name: str) -> str:
    """
    查看某个插件的详细信息，包括可识别触发词、状态和用法。

    Args:
        plugin_name (str): 插件名、显示名或别名
    """
    event = current_event.get(None)
    return plugin_index.render_plugin_detail(plugin_name, event=event)


@nb_langchain_tool
async def invoke_project_plugin(plugin_name: str, command: str = "") -> str:
    """
    按插件名触发插件。建议先调用 search_project_plugins 或 inspect_project_plugin，再传入完整命令。
    如果当前用户消息中已经包含图片，本工具会自动把当前图片一起交给插件，
    适用于二维码、OCR、图片处理等依赖图片输入的插件，不需要让用户重新发图。

    Args:
        plugin_name (str): 插件名、显示名或别名
        command (str): 要发送给插件的完整命令
    """
    event = current_event.get(None)
    entry = plugin_index.resolve(plugin_name)
    if entry is None:
        return f"找不到插件“{plugin_name}”，请先搜索插件。"
    if blocked_reason := _blocked_plugin_reason(entry.plugin_name):
        return blocked_reason

    availability = plugin_index.get_availability(entry.plugin_name, event)
    if not availability.available:
        return f"插件 {entry.short_label()} 当前不可调用：{availability.status_text}"

    if not command:
        default_command = entry.default_command()
        if not default_command:
            detail = plugin_index.render_plugin_detail(entry.plugin_name, event=event)
            return (
                f"插件 {entry.short_label()} 没有可直接自动补全的固定触发词，请根据下面信息组织完整命令后再调用：\n"
                f"{detail}"
            )
        command = default_command

    attach_current_images = any(
        seg.type == "image" for seg in getattr(event, "message", [])
    )
    if attach_current_images:
        removable_urls = _collect_current_image_urls(event)
        command = _sanitize_command_for_attached_images(
            command,
            fallback_command=entry.default_command() or entry.display_name,
            removable_urls=removable_urls,
        )
    return await _dispatch_plugin_command(
        command,
        attach_current_images=attach_current_images,
    )
