import secrets

from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    GroupMessageEvent,
    Message,
    ActionFailed,
    Bot,
    MessageSegment,
)
from nonebot.log import logger
from nonebot import on_command
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg

from .data_source import get_event_zhanbu, get_eorzean_zhanbu

__plugin_meta__ = PluginMetadata(
    name="艾欧泽亚占卜",
    description="艾欧泽亚占卜",
    usage="""
usage：
    /占卜
    /占卜 [事件]
""".strip(),
    extra={
        "unique_name": "migang_eorzean_占卜",
        "example": "/占卜\n/占卜 今天下雪吗",
        "author": "migang",
        "version": 0.1,
    },
)

__pluginc_categroy__ = "好玩的"

eorzean_zhanbu = on_command(
    cmd="/占卜", aliases={"、占卜", "/zhanbu"}, priority=5, block=True
)

kExceptionNotice = ("占卜水晶球滑落了~正在重新捡起(擦擦)", "水晶球化为碎片，正在尝试重组~", "星天开门！")


@eorzean_zhanbu.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        if msg != "":
            await eorzean_zhanbu.finish(get_event_zhanbu(event.user_id, msg))
        else:
            if isinstance(event, GroupMessageEvent):
                nickname = await bot.get_group_member_info(
                    group_id=event.group_id, user_id=event.user_id
                )
                nickname = nickname.get("card") or nickname["nickname"]
            else:
                nickname = (await bot.get_stranger_info(user_id=event.user_id))[
                    "nickname"
                ]
            if not nickname:
                if isinstance(event, GroupMessageEvent):
                    nickname = event.sender.card or event.sender.nickname
                else:
                    nickname = event.sender.nickname
            await eorzean_zhanbu.finish(
                f"{nickname}({event.user_id})\n"
                + MessageSegment.image(await get_eorzean_zhanbu(event.user_id))
            )
    except ActionFailed:
        logger.warning("占卜失败")
        await eorzean_zhanbu.finish(secrets.choice(kExceptionNotice), at_sender=True)