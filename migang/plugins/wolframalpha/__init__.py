"""
https://github.com/MeetWq/mybot/tree/master/src/plugins/wolfram
"""
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message

from migang.core import ConfigItem, get_config

from .data_source import get_wolframalpha_simple

__plugin_meta__ = PluginMetadata(
    name="知识计算引擎",
    description="WolframAlpha计算知识引擎",
    usage="""
指令：
    wolfram 文本
示例：
    wolfram int x
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)


__plugin_config__ = ConfigItem(
    key="wolframalpha_appid",
    description="从 https://developer.wolframalpha.com/portal/myapps/index.html 获取",
)

wolfram = on_command("wolfram", aliases={"wolframalpha"}, block=True, priority=12)


@wolfram.handle()
async def _(msg: Message = CommandArg()):
    text = msg.extract_plain_text()
    if not text:
        await wolfram.finish("请在指令后接文本哦~")

    appid = await get_config("wolframalpha_appid")
    res = await get_wolframalpha_simple(text, appid)
    if not res:
        await wolfram.finish("出错了，请稍后再试")

    await wolfram.finish(res)
