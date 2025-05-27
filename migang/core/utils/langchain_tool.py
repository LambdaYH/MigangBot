from functools import wraps

from langchain_core.tools import tool
from nonebot.matcher import current_matcher
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core.core_plugins.chat.chatgpt.langchain_tools import tool_manager


def nb_langchain_tool(func):
    @tool
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if isinstance(result, (Message, MessageSegment)):
            matcher = current_matcher.get(None)
            if matcher is not None:
                await matcher.send(result)
                return "工具调用内容已发送"

        return result

    tool_manager.register_tool(wrapper)
    return wrapper
