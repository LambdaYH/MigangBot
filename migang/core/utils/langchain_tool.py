import inspect
from functools import wraps

import anyio
from nonebot.log import logger
from nonebot.typing import T_State
from langchain_core.tools import tool
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher, current_matcher
from nonebot.utils import run_sync, is_coroutine_callable
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core.core_plugins.chat_agent.plugin_index import plugin_index
from migang.core.core_plugins.chat_agent.langchain_tools import tool_manager

# 需要自动注入的上下文类型
INJECT_TYPES = (Matcher, Bot, Event, T_State, Message)


def _format_tool_log_value(value, max_length: int = 300) -> str:
    text = str(value)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def nb_langchain_tool(func):
    @tool
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"开始调用Tool：{func.__name__}")
        # 兼容同步和异步工具函数
        if is_coroutine_callable(func):
            result = await func(*args, **kwargs)
        else:
            result = await run_sync(func)(*args, **kwargs)
        if isinstance(result, (Message, MessageSegment)):
            matcher = current_matcher.get(None)
            if matcher is not None:
                await matcher.send(result)
                result = "已成功调用该工具，工具结果已直接提供给用户，请勿再次调用"
        logger.info(f"Tool调用结果：{_format_tool_log_value(result)}")
        return result

    tool_manager.register_tool(wrapper)
    return wrapper


async def search_plugin_tool(query: str, has_image: bool = False) -> str:
    """
    工具描述：根据用户问题检索最相关的插件，并返回插件详细信息。
    参数:
        query: 用户问题
    """
    return plugin_index.render_prompt_context(query, has_image=has_image)
