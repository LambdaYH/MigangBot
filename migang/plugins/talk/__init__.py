from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import CountItem
from migang.utils.tts import get_azure_tts, azure_tts_status
from migang.utils.text import filt_message

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="说",
    description="Bot说话啦",
    usage="""
usage：
    指令：
        说xxxx，需要@bot
""".strip(),
    extra={
        "unique_name": "migang_talk",
        "example": "缩写 hhsh",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "好玩的"
__plugin_count__ = CountItem(count=5, hint="说不动了...")

talk = on_command("说", aliases={"talk", "讲"}, priority=5, rule=to_me(), block=True)


@talk.handle()
async def _(arg: Message = CommandArg()):
    if not azure_tts_status():
        await talk.finish("咿呀呜啊！（未配置tts）")
    await talk.send(
        MessageSegment.record(
            await get_azure_tts(filt_message(arg.extract_plain_text().strip()))
        )
    )
