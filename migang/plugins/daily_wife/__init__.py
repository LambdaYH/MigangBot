"""
https://github.com/SonderXiaoming/dailywife
"""
from random import choice
from datetime import datetime

from nonebot.params import Depends
from nonebot import require, on_fullmatch
from nonebot.plugin import PluginMetadata
from sqlalchemy.ext.asyncio.session import AsyncSession
from nonebot.adapters.onebot.v11 import GROUP, Bot, MessageSegment, GroupMessageEvent

from migang.utils.image import get_user_avatar

require("nonebot_plugin_datastore")
from sqlalchemy import select
from nonebot_plugin_datastore import get_session

from .model import DailyWife

__plugin_meta__ = PluginMetadata(
    name="今日老婆",
    description="抓到今日的群友老婆",
    usage="""
usage：
    发送[今日老婆]
    随机抓取群友作为老婆
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "好玩的"

laopo = on_fullmatch(
    "今日老婆",
    permission=GROUP,
    priority=26,
    block=True,
)


async def get_wife_info(member_info, qqid):
    avatar = await get_user_avatar(qqid, 640)
    member_name = member_info["card"] or member_info["nickname"]
    result = "今天的群友老婆是:" + MessageSegment.image(avatar) + f"{member_name}({qqid})"
    return result


@laopo.handle()
async def _(
    bot: Bot, event: GroupMessageEvent, session: AsyncSession = Depends(get_session)
):
    wife_id: int = None
    if event.get_user_id() in bot.config.superusers:
        wife_id = event.self_id
    else:
        user_wife_info = await session.scalar(
            select(DailyWife).where(
                DailyWife.user_id == event.user_id, DailyWife.group_id == event.group_id
            )
        )
        if user_wife_info and user_wife_info.time.date() == datetime.now().date():
            wife_id = user_wife_info.wife_id
        else:
            group_member_list = await bot.get_group_member_list(group_id=event.group_id)
            group_member_set = set([member["user_id"] for member in group_member_list])
            today_exist_wife = set(
                [
                    wife.wife_id
                    for wife in (
                        await session.scalars(
                            select(DailyWife).where(
                                DailyWife.time >= datetime.now().date()
                            )
                        )
                    ).all()
                ]
            )
            group_member_set -= today_exist_wife
            if event.self_id in group_member_set:
                group_member_set.remove(event.self_id)
            if event.user_id in group_member_set:
                group_member_set.remove(event.user_id)
            if not group_member_set:
                await laopo.finish("所有群友都已经配对了哦~明天早些来吧")
            wife_id = choice(list(group_member_set))
            if not user_wife_info:
                user_wife_info = DailyWife(
                    user_id=event.user_id,
                    group_id=event.group_id,
                    wife_id=wife_id,
                    time=datetime.now(),
                )
                session.add(user_wife_info)
            else:
                user_wife_info.wife_id = wife_id
                user_wife_info.time = datetime.now()
    member_info = await bot.get_group_member_info(
        group_id=event.group_id, user_id=wife_id
    )
    nickname = event.sender.card or event.sender.nickname
    result = f"{nickname}({event.sender.user_id})\n" + await get_wife_info(
        member_info, wife_id
    )
    await laopo.send(result)
    await session.commit()
