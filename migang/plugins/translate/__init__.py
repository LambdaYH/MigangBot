import re
import asyncio

import aiohttp
from nonebot.log import logger
from nonebot.params import Startswith, EventPlainText
from nonebot.plugin import PluginMetadata
from nonebot import get_driver, on_startswith
from nonebot.adapters.onebot.v11 import Bot, Message, GroupMessageEvent, MessageEvent

from migang.core import ConfigItem, get_config

from .data_source import (
    get_azure_trans,
    get_baidu_trans,
    get_deepl_trans,
    get_google_trans,
    get_youdao_trans,
    baidu_language,
    google_language,
    get_language_form,
)

__plugin_meta__ = PluginMetadata(
    name="翻译",
    description="将多个语言翻译成中文，提供多翻译源结果",
    usage=f"""[md][width=900]
## 将多个语言翻译成中文，提供多翻译源结果
### 指令
- 翻译 xxxx
- 翻译to:语言 xxx
---
### 当添加`to:语言`参数时，仅启用谷歌、百度翻译
#### 谷歌翻译支持的语言有
{get_language_form(google_language)}

#### 百度翻译支持的语言有
{get_language_form(baidu_language)}
""".strip(),
    extra={
        "unique_name": "migang_translate",
        "example": "翻译 hello",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "一些工具"
__plugin_config__ = (
    ConfigItem(key="baidu_app_id", description="百度翻译APPID"),
    ConfigItem(key="baidu_api_key", description="百度翻译API_KEY"),
    ConfigItem(key="deepl_api_key", description="Deepl翻译API_KEY"),
    ConfigItem(key="azure_api_key", description="微软Azure翻译 subscriptionKey"),
)


translate = on_startswith("翻译", priority=5, block=True)

GOOGLE_STATUS = False


@get_driver().on_startup
async def _():
    global GOOGLE_STATUS
    try:
        async with aiohttp.ClientSession() as client:
            r = await client.head("https://translate.google.com/", timeout=2)
            GOOGLE_STATUS = r.status == 200
    except asyncio.exceptions.TimeoutError:
        logger.info("无法连接谷歌翻译，谷歌翻译已禁用")


@translate.handle()
async def _(
    bot: Bot,
    event: MessageEvent,
    plain_text: str = EventPlainText(),
    cmd: str = Startswith(),
):
    text = plain_text.removeprefix(cmd).strip()
    to = None
    if match := re.search("^to:(\S+)"):
        to = match.group(1)
        text = text.removeprefix(match.group(0)).strip()
    tasks = []
    if to is None:
        tasks.append(
            get_youdao_trans(text),
        )
        if GOOGLE_STATUS:
            tasks.append(get_google_trans(text))
        if await get_config("baidu_api_key"):
            tasks.append(get_baidu_trans(text))
        if await get_config("azure_api_key"):
            tasks.append(get_azure_trans(text))
        if await get_config("deepl_api_key"):
            tasks.append(get_deepl_trans(text))
    else:
        if GOOGLE_STATUS:
            tasks.append(get_google_trans(text=text, to=to))
        if await get_config("baidu_api_key"):
            tasks.append(get_baidu_trans(text, to=to))
    msg = await asyncio.gather(*tasks)
    if msg and len(max(msg, key=len)) < 60:
        await translate.finish("\n".join(msg))
    msg = [
        {
            "type": "node",
            "data": {
                "name": "翻译威",
                "uin": f"{bot.self_id}",
                "content": m,
            },
        }
        for m in msg
    ]
    if isinstance(event, GroupMessageEvent):
        await bot.send_forward_msg(group_id=event.group_id, messages=msg)
    else:
        await bot.send_forward_msg(user_id=event.user_id, messages=msg)
