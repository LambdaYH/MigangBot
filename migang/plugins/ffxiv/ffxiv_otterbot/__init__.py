import asyncio

from nonebot.drivers import Driver
from nonebot.plugin import PluginMetadata
from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import MessageEvent

from migang.core import ConfigItem, get_config

from .filter import command_filter
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

is_matcher_created = False

ws_conn: WebSocketConn


def _rule(event: MessageEvent):
    return command_filter(event.get_plaintext())


async def _message_handler(event: MessageEvent):
    await ws_conn.forwardEvent(event)


@driver.on_startup
async def setup_ws():
    access_token = await get_config("access_token")
    if not access_token:
        return
    bot_id = await get_config("bot_id")
    if not bot_id:
        return
    url = await get_config("url")
    if not url:
        return
    global ws_conn
    ws_conn = WebSocketConn(url=url, bot_id=bot_id, access_token=access_token)
    asyncio.create_task(ws_conn.connect())
    on_message(block=False, rule=_rule).append_handler(_message_handler)
