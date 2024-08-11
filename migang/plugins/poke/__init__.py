import random
import asyncio

from nonebot import on_notice
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageSegment, PokeNotifyEvent

from migang.core.models import UserProperty

__zx_plugin_name__ = "戳一戳"

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="戳一戳",
    description="简单的戳一戳",
    usage="",
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_cd__ = 3


def _rule(event: PokeNotifyEvent):
    return event.self_id == event.target_id


poke = on_notice(priority=5, block=False, rule=_rule)

face_candidates_other = [181, 351]
face_candidates_level5 = [350, 341]
face_candidates_level7 = [319]


@poke.handle()
async def _(event: PokeNotifyEvent):
    impression = await UserProperty.get_impression(user_id=event.user_id)
    print(impression)
    ca = []
    if impression >= 680:
        ca += face_candidates_level5
    if impression >= 2500:
        ca += face_candidates_level7
    if len(ca) == 0:
        ca = face_candidates_other
    # 1-4秒延迟
    await asyncio.sleep(random.random() * 3 + 1)
    await poke.send(MessageSegment.face(random.choice(ca)))
