import random
import asyncio

from nonebot import on_notice
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageSegment, PokeNotifyEvent

__zx_plugin_name__ = "戳一戳"

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="戳一戳",
    description="简单的戳一戳",
    usage="",
    extra={
        "unique_name": "migang_poke",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_cd__ = 3


def _rule(event: PokeNotifyEvent):
    return event.self_id == event.target_id


poke = on_notice(priority=5, block=False, rule=_rule)


@poke.handle()
async def _(event: PokeNotifyEvent):
    # 1-4秒延迟
    await asyncio.sleep(random.random() * 3 + 1)
    await poke.send(MessageSegment("poke", {"qq": event.user_id}))
