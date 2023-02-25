"""
https://github.com/SonderXiaoming/dailywife
"""
import datetime
from random import choice

from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import GROUP, Bot, MessageSegment, GroupMessageEvent

from migang.core import DATA_PATH
from migang.utils.image import get_user_avatar
from migang.utils.file import async_load_data, async_save_data

__plugin_meta__ = PluginMetadata(
    name="今日老婆",
    description="艾欧泽亚占卜",
    usage="""
usage：
    发送[今日老婆]
    随机抓取群友作为老婆
""".strip(),
    extra={
        "unique_name": "migang_daily_wife",
        "example": "今日老婆",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "好玩的"

laopo = on_fullmatch(
    "今日老婆",
    permission=GROUP,
    priority=26,
    block=True,
)

data_path = DATA_PATH / "daily_wife"


def get_member_set(all_list):
    id_set = set()
    for member_list in all_list:
        id_set.add(member_list["user_id"])
    return id_set


async def get_wife_info(member_info, qqid):
    avatar = await get_user_avatar(qqid, 640)
    member_name = member_info["card"] or member_info["nickname"]
    result = "今天的群友老婆是:" + MessageSegment.image(avatar) + f"{member_name}({qqid})"
    return result


async def load_group_config(group_id: str):
    if not data_path.exists():
        data_path.mkdir(parents=True, exist_ok=True)
    return await async_load_data(data_path / f"{group_id}.json")


async def write_group_config(
    group_id: str, user_id: str, wife_id: int, date: str, config
):
    config_file = data_path / f"{group_id}.json"
    config[user_id] = [wife_id, date]
    await async_save_data(config, config_file)


@laopo.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    groupid = event.group_id
    user_id = event.user_id
    user_id_str = str(user_id)
    self_id = event.self_id
    wife_id = None
    today = str(datetime.date.today())
    config = await load_group_config(groupid)

    if user_id_str in bot.config.superusers:
        wife_id = self_id
    elif user_id_str in config and config[user_id_str][1] == today:
        wife_id = config[user_id_str][0]

    if not wife_id:
        all_list = await bot.get_group_member_list(group_id=groupid)
        id_set = get_member_set(all_list)
        for record_id in list(config):
            if config[record_id][1] == today:
                if not config[record_id][0] in id_set:
                    del config[record_id]
                else:
                    id_set.remove(config[record_id][0])
        if self_id in id_set:
            id_set.remove(self_id)
        if user_id in id_set:
            id_set.remove(user_id)

        wife_id = choice(list(id_set))

    await write_group_config(groupid, user_id_str, wife_id, today, config)
    member_info = await bot.get_group_member_info(group_id=groupid, user_id=wife_id)
    nickname = event.sender.card or event.sender.nickname
    result = f"{nickname}({event.sender.user_id})\n" + await get_wife_info(
        member_info, wife_id
    )
    await laopo.send(result)
