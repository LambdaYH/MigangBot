from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11 import Bot, MessageSegment, GroupMessageEvent

from .data_source import handle_sign_in

__plugin_meta__ = PluginMetadata(
    name="签到",
    description="签到会发生什么呢",
    usage="""
usage：
    签到，数据以用户为单位
    指令：
        签到
""".strip(),
    extra={
        "unique_name": "migang_sign_in",
        "example": "签到",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "基础功能"

sign_in = on_fullmatch("签到", priority=5, permission=GROUP, block=True)


@sign_in.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    nickname = event.sender.card or event.sender.nickname
    await sign_in.send(
        MessageSegment.image(
            await handle_sign_in(
                user_id=event.user_id,
                user_name=nickname,
                bot_name=list(bot.config.nickname)[0],
            )
        )
    )
