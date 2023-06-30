from nonebot.rule import to_me
from nonebot import on_startswith
from nonebot.params import Startswith
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment

from migang.core import CountItem
from migang.utils.text import filt_message
from migang.utils.tts import get_azure_tts, azure_tts_status

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="说",
    description="Bot说话啦",
    usage="""
usage：
    指令：
        说xxxx，需要@bot
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "好玩的"
__plugin_count__ = CountItem(count=5, hint="说不动了...")

talk = on_startswith(("说", "讲"), priority=5, rule=to_me(), block=True)


@talk.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    if not azure_tts_status():
        await talk.finish("咿呀呜啊！（未配置tts）")
    await talk.send(
        MessageSegment.record(
            await get_azure_tts(
                filt_message(event.get_plaintext().removeprefix(cmd).strip())
            )
        )
    )
