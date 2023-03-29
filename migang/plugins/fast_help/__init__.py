from nonebot.params import Startswith
from nonebot import require, on_startswith
from nonebot.plugin import PluginMetadata
from nonebot import require
from nonebot.adapters.onebot.v11 import MessageEvent

import anyio

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="快速呼出帮助",
    description="很多人都喜欢用/+插件名，所以就用这个插件来在调用/且匹配到插件时候呼出帮助",
    usage="""
usage：
    /插件名
""".strip(),
    extra={
        "unique_name": "migang_fast_help",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

require("help")
from migang.core.core_plugins.help.data_source import get_plugin_help, draw_usage

fast_help = on_startswith("/", priority=955, block=False)


@fast_help.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    plugin_name = event.get_plaintext().removeprefix(cmd).strip()
    if usage := get_plugin_help(name=plugin_name):
        print(usage)
        await fast_help.send(await anyio.to_thread.run_sync(draw_usage, usage))
