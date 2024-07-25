import asyncio
from typing import Union

import websockets
from nonebot.log import logger
from nonebot.adapters import Event
from nonebot.plugin import PluginMetadata
from nonebot import get_driver, on_message
from websockets.legacy.client import Connect
from websockets.exceptions import ConnectionClosedError
from nonebot.drivers import Driver, Request, WebSocketClientMixin
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from migang.core import ConfigItem, get_config

from .websocket import WebSocketConn

__plugin_meta__ = PluginMetadata(
    name="otterbot",
    description="连接到獭窝",
    usage="""
usage：
    将一些指令转发到獭窝
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "FF14"
__plugin_hidden__ = True

__plugin_config__ = (
    ConfigItem(
        key="url",
        initial_value="wss://xn--v9x.net/ws",
        description="獭窝地址，主窝wss://xn--v9x.net/ws",
    ),
    ConfigItem(
        key="bot_id",
        description="獭窝中配置的bot_id",
    ),
    ConfigItem(key="access_token", description="token"),
)

driver: Driver = get_driver()

ws_conn: WebSocketConn


@driver.on_bot_connect
async def setup_ws(bot: Bot):
    access_token = await get_config("access_token")
    if not access_token:
        return
    bot_id = await get_config("bot_id")
    if not bot_id:
        bot_id = bot.self_id
    url = await get_config("url")
    if not url:
        return
    global ws_conn
    ws_conn = WebSocketConn(bot=bot, url=url, bot_id=bot_id, access_token=access_token)
    asyncio.gather(ws_conn.connect())


handle_message = on_message(block=False)


@handle_message.handle()
async def _(event: MessageEvent):
    await ws_conn.forwardEvent(event)
