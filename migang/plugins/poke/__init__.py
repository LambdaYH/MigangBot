from nonebot import on_notice
from nonebot.adapters.onebot.v11 import PokeNotifyEvent, MessageSegment


from nonebot.plugin import PluginMetadata

__zx_plugin_name__ = "戳一戳"

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="戳一戳",
    description="简单的戳一戳",
    usage="""
usage：
    搜pdf xxx
""".strip(),
    extra={
        "unique_name": "migang_poke",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)


def _rule(event: PokeNotifyEvent):
    return event.self_id == event.target_id


poke = on_notice(priority=5, block=False, rule=_rule)


@poke.handle()
async def _(event: PokeNotifyEvent):
    await poke.send(MessageSegment.poke(id_=event.target_id))