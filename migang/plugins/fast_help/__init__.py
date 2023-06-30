from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
from nonebot import require, on_startswith
from nonebot.adapters.onebot.v11 import MessageEvent

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="快速呼出帮助",
    description="很多人都喜欢用/+插件名，所以就用这个插件来在调用/且匹配到插件时候呼出帮助",
    usage="""
usage：
    /插件名
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

require("help")
from migang.core.core_plugins.help.data_source import draw_usage, get_plugin_help


def _rule(event: MessageEvent, state: T_State) -> bool:
    if usage := get_plugin_help(name=event.get_plaintext()[1:].strip()):
        state["_usage"] = usage
        return True
    return False


fast_help = on_startswith("/", priority=955, block=False, rule=_rule)


@fast_help.handle()
async def _(state: T_State):
    await fast_help.send(await draw_usage(state["_usage"]))
