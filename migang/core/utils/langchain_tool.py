import inspect
from functools import wraps

import anyio
from nonebot.typing import T_State
from langchain_core.tools import tool
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher, current_matcher
from nonebot.utils import run_sync, is_coroutine_callable
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core.core_plugins.chat.chatgpt.langchain_tools import tool_manager
from migang.core.core_plugins.chat.chatgpt.plugin_vector_db import search_plugin

# 需要自动注入的上下文类型
INJECT_TYPES = (Matcher, Bot, Event, T_State, Message)


def nb_langchain_tool(func):
    @tool
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 兼容同步和异步工具函数
        if is_coroutine_callable(func):
            result = await func(*args, **kwargs)
        else:
            result = await run_sync(func)(*args, **kwargs)
        if isinstance(result, (Message, MessageSegment)):
            matcher = current_matcher.get(None)
            if matcher is not None:
                await matcher.send(result)
                return "已成功调用该工具，工具结果已直接提供给用户，请勿再次调用"
        return result

    tool_manager.register_tool(wrapper)
    # 打印当前所有工具名称
    return wrapper


async def search_plugin_tool(query: str) -> str:
    """
    工具描述：根据用户问题检索最相关的插件，并返回插件详细信息。
    参数:
        query: 用户问题
    """
    return await search_plugin(query)
