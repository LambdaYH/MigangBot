import asyncio

from nonebot.log import logger
from nonebot.drivers import Driver
from nonebot.plugin import PluginMetadata
from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import MessageEvent

from migang.core import ConfigItem, get_config, post_init_manager

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

__plugin_config__ = ConfigItem(
    key="bots",
    initial_value=[
        {"bot": "12345", "url": "wss://xn--v9x.net/ws", "access_token": "獭窝的token"}
    ],
    description="bot：獭窝的botqq\nurl：獭窝连接地址\naccess_token：獭窝的token",
)

driver: Driver = get_driver()

is_matcher_created = False

__bot_ws_conn = {}


def _rule(event: MessageEvent):
    return command_filter(event.get_plaintext())


handle_msg = on_message(block=False, rule=_rule)


@handle_msg.handle()
async def _(event: MessageEvent):
    if ws_conn := __bot_ws_conn.get(event.self_id):
        await ws_conn.forwardEvent(event)


@post_init_manager
async def setup_ws():
    bots = await get_config("bots")
    if not bots:
        return
    for bot in bots:
        if "bot" not in bot or "url" not in bot or "access_token" not in bot:
            logger.error(f"獭窝配置错误")
            return
        bot_id = int(bot["bot"])
        url = bot["url"]
        ws_conn = WebSocketConn(
            url=url, bot_id=bot_id, access_token=bot["access_token"]
        )
        __bot_ws_conn[bot_id] = ws_conn
        asyncio.create_task(ws_conn.connect())
