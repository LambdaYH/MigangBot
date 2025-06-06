import random
import asyncio
from typing import Any, Tuple

import aiohttp
from aiocache import cached
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.params import RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot import on_regex, get_driver, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
)

from migang.core import CDItem, CountItem
from migang.utils.file import async_load_data

from .data_source import DATA_PATH, update_suits_img

__plugin_meta__ = PluginMetadata(
    name="闪暖图库",
    description="来看看暖女儿的衣柜吧！",
    usage="""
usage：
    来看看暖女儿的衣柜吧！
    指令：
        随机暖暖
        n连随机暖暖

        闪暖套装
        n连闪暖套装（n <= 9）
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "好看的"
__plugin_cd__ = CDItem(3, hint="心急穿不了大裙子！")
__plugin_count__ = CountItem(126, hint="今天看太多啦！留点明天看吧")

suit_draw = on_regex(r"^(\d)?连?闪暖套装$", priority=5, block=True)
update_suits = on_fullmatch(
    "更新闪暖套装", priority=1, rule=to_me(), permission=SUPERUSER, block=True
)
random_nikki = on_regex(r"^(\d)?连?随机暖暖$", priority=5, block=True)


@cached(ttl=600)
async def get_data():
    return await async_load_data(DATA_PATH / "suits.json")


@suit_draw.handle()
async def _(bot: Bot, event: MessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    num = int(reg_group[0] or 1)
    suits = await get_data()
    if num <= 1:
        id_ = random.choice(list(suits.keys()))
        await suit_draw.finish(
            MessageSegment.image(DATA_PATH / "suits" / f"{id_}.jpg")
            + f"\n套装名：{suits[id_]['name']}"
        )
    msgs = []
    suits_list = list(suits.keys())
    random.shuffle(suits_list)
    num = min(len(suits), num)
    for i in range(num):
        msgs.append(
            MessageSegment.node_custom(
                user_id=event.self_id,
                nickname="苏暖暖",
                content=MessageSegment.image(
                    DATA_PATH / "suits" / f"{suits_list[i]}.jpg"
                )
                + f"\n套装名：{suits[suits_list[i]]['name']}",
            )
        )
    if isinstance(event, GroupMessageEvent):
        await bot.send_forward_msg(group_id=event.group_id, messages=msgs)
    else:
        await bot.send_forward_msg(user_id=event.user_id, messages=msgs)


@update_suits.handle()
async def _():
    await update_suits.send("开始更新闪暖套装图片")
    try:
        insert_count, download_count = await update_suits_img()
        await update_suits.send(
            f"更新闪暖套装图片成功，已新添加{insert_count}套套装，新下载{download_count}张图片"
        )
    except Exception as e:
        logger.warning(f"更新闪暖套装图片失败：{e}")
        await update_suits.send("更新闪暖套装图片失败")


@get_driver().on_startup
async def _():
    logger.info("正在检测闪暖套装图片更新...")
    asyncio.create_task(update_suits_img())


@random_nikki.handle()
async def _(bot: Bot, event: MessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    num = int(reg_group[0] or 1)
    async with aiohttp.ClientSession() as client:
        r = await client.get(
            "https://api.sunuannuan.com/api/assets",
            params={"category": "nikki", "count": num},
            timeout=6,
        )
        r = await r.json()
        if num == 1:
            await random_nikki.send(MessageSegment.image(r["data"][0]["url"]))
        else:
            msgs = [
                MessageSegment.node_custom(
                    user_id=event.self_id,
                    nickname="苏暖暖",
                    content=MessageSegment.image(img["url"]),
                )
                for img in r["data"]
            ]
            if isinstance(event, GroupMessageEvent):
                await bot.send_forward_msg(group_id=event.group_id, messages=msgs)
            else:
                await bot.send_forward_msg(user_id=event.user_id, messages=msgs)
