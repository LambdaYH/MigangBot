import os
import random
from functools import wraps

import openai
from langchain_core.tools import tool
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core import sync_get_config
from migang.core.utils.langchain_tool import nb_langchain_tool

# 获取openai相关配置，与langchain一致
api_keys = sync_get_config("api_keys", "chat_chatgpt", [])
api_base = sync_get_config("api_base", "chat_chatgpt", "")
proxy = sync_get_config("proxy", "chat_chatgpt", "")

api_key = api_keys[0] if api_keys else os.getenv("OPENAI_API_KEY", "")

client_args = {"api_key": api_key}
if api_base:
    client_args["base_url"] = api_base

async_openai = openai.AsyncOpenAI(**client_args)


@nb_langchain_tool
async def paint_image(content: str) -> object:
    """
    根据用户的描述生成图片。
    强烈建议：只要用户的请求涉及"画画"、"图片"、"插画"、"生成图像"、"画一张"、"画个"、"画幅"、"画出"、"生成图片"、"生成插画"等内容，都应优先调用本工具，而不是直接回复文本。

    Args:
        content (str): 用户的描述词语，比如"画一个西瓜"或"画一只猫"。

    Returns:
        Message: 包含图片和说明文字的消息对象，或错误提示字符串。
    """
    response = await async_openai.images.generate(
        model="Kwai-Kolors/Kolors",
        prompt=content,
        n=1,
        size="1024x1024",
    )
    image_url = response.data[0].url
    if image_url:
        # 返回Message对象，图片和说明文字分开发送
        return Message([MessageSegment.image(image_url), MessageSegment.text("画好了！")])
    else:
        return "画笔没墨了..."
