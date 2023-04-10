import os
import uuid

import openai
from transformers import GPT2TokenizerFast

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

import anyio
import requests

from migang.core import get_config

from ..extension import extension_manager

# 拓展的配置信息，用于ai理解拓展的功能 *必填*
ext_config: dict = {
    "name": "paint",  # 拓展名称，用于标识拓展
    "arguments": {
        "content": "str",  # 绘画内容描述
    },
    "description": "paint a picture，使用/#paint&CONTENT#/，其中CONTENT是用逗号分隔的描述性词语。(例如：/#paint&兔子,草地,彩虹#/)",
    # 参考词，用于上下文参考使用，为空则每次都会被参考(消耗token)
    "refer_word": ["paint", "画", "图"],
    # 每次消息回复中最大调用次数，不填则默认为99
    "max_call_times_per_msg": 3,
    # 作者信息
    "author": "OREOREO",
    # 版本
    "version": "0.0.1",
    # 拓展简介
    "intro": "绘图",
}


@extension_manager(
    name="paint",
    description="paint a picture，使用/#paint&CONTENT#/，其中CONTENT是用逗号分隔的描述性词语。(例如：/#paint&兔子,草地,彩虹#/)",
    refer_word=["paint", "画", "图"],
)
async def _(content: str):
    proxy = await get_config("proxy", "chat_chatgpt")
    if proxy:
        if not proxy.startswith("http"):
            proxy = "http://" + proxy
        openai.proxy = proxy
    custom_size = (512, 512)
    # style = "anime style, colored-pencil"
    style = "Chinese style, ink painting"
    response = await openai.Image.acreate(
        prompt=content + ", " + style, n=1, size=f"{custom_size[0]}x{custom_size[1]}"
    )
    image_url = response["data"][0]["url"]

    if image_url is None:
        return {
            "text": "图片生成错误...",
            "image": None,  # 图片url
        }
    elif "rejected" in response:
        # 返回的信息将会被发送到会话中
        return {
            "text": "抱歉，这个图违反了ai生成规定，可能是太色了吧",  # 文本信息
            "image": None,  # 图片url
        }
    else:
        # 返回的信息将会被发送到会话中
        return {
            "text": "画好了!",  # 文本信息
            "image": image_url,  # 图片url
        }
