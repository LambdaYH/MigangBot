import random

from langchain_core.tools import tool
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import get_config

async_openai = openai.AsyncOpenAI(api_key="")


@tool
async def paint_image(content: str) -> object:
    """绘制图片工具，content为描述词语，返回NoneBot2 MessageSegment或字符串"""
    from ..asyncopenai import async_openai

    proxy = await get_config("proxy", "chat_chatgpt")
    if proxy:
        if not proxy.startswith("http"):
            proxy = "http://" + proxy
        async_openai.proxy = proxy
    style_preset = (
        "Chinese style, ink painting",
        "anime style, colored-pencil",
        "anime style, colored crayons",
    )
    style = random.choice(style_preset)
    response = await async_openai.images.generate(
        model="Kwai-Kolors/Kolors",
        prompt=content + ", " + style,
        n=1,
        size="1024x1024",
    )
    image_url = response.data[0].url
    if image_url:
        return MessageSegment.image(image_url)
    else:
        return "画笔没墨了..."
