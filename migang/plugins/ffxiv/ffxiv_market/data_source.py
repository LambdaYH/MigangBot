import re
import time
import asyncio
import traceback
from typing import Union, Optional
from difflib import SequenceMatcher

import aiohttp
from nonebot.log import logger
from tenacity import RetryError, retry, stop_after_attempt


def localize_world_name(world_name: str):
    world_dict = {
        "HongYuHai": "红玉海",
        "ShenYiZhiDi": "神意之地",
        "LaNuoXiYa": "拉诺西亚",
        "HuanYingQunDao": "幻影群岛",
        "MengYaChi": "萌芽池",
        "YuZhouHeYin": "宇宙和音",
        "WoXianXiRan": "沃仙曦染",
        "ChenXiWangZuo": "晨曦王座",
        "BaiYinXiang": "白银乡",
        "BaiJinHuanXiang": "白金幻象",
        "ShenQuanHen": "神拳痕",
        "ChaoFengTing": "潮风亭",
        "LvRenZhanQiao": "旅人栈桥",
        "FuXiaoZhiJian": "拂晓之间",
        "Longchaoshendian": "龙巢神殿",
        "MengYuBaoJing": "梦羽宝境",
        "ZiShuiZhanQiao": "紫水栈桥",
        "YanXia": "延夏",
        "JingYuZhuangYuan": "静语庄园",
        "MoDuNa": "摩杜纳",
        "HaiMaoChaWu": "海猫茶屋",
        "RouFengHaiWan": "柔风海湾",
        "HuPoYuan": "琥珀原",
        "ShuiJingTa2": "水晶塔",
        "YinLeiHu2": "银泪湖",
        "TaiYangHaiAn2": "太阳海岸",
        "YiXiuJiaDe2": "伊修加德",
        "HongChaChuan2": "红茶川",
    }
    for k, v in world_dict.items():
        pattern = re.compile(k, re.IGNORECASE)
        world_name = pattern.sub(v, world_name)
    return world_name


@retry(stop=stop_after_attempt(3))
async def get_item_id(
    item_name: str, client: aiohttp.ClientSession, name_lang: Optional[str] = None
) -> Union[Optional[str], int]:
    params = {"indexes": "Item", "string": item_name}
    if name_lang is not None:
        params["language"] = name_lang

    url = "https://xivapi.com/search"
    if name_lang == "cn":
        url = "https://cafemaker.wakingsands.com/search"
    r = await client.get(url=url, timeout=30, params=params)
    result = (await r.json())["Results"]
    if len(result) > 0:
        result = max(
            result,
            key=lambda x: SequenceMatcher(None, x["Name"], item_name).ratio(),
        )
        return result["Name"], result["ID"]
    return None, -1


def handle_item_name_abbr(item_name: str):
    if item_name.startswith("第二期重建用的") and item_name.endswith("(检)"):
        item_name = item_name.replace("(", "（").replace(")", "）")
    if item_name.startswith("第二期重建用的") and not item_name.endswith("（检）"):
        item_name = item_name + "（检）"
    if item_name.upper() == "G12":
        item_name = "陈旧的缠尾蛟革地图"
    if item_name.upper() == "G11":
        item_name = "陈旧的绿飘龙革地图"
    if item_name.upper() == "G10":
        item_name = "陈旧的瞪羚革地图"
    if item_name.upper() == "G9":
        item_name = "陈旧的迦迦纳怪鸟革地图"
    if item_name.upper() == "G8":
        item_name = "陈旧的巨龙革地图图"
    if item_name.upper() == "G7":
        item_name = "陈旧的飞龙革地图"
    return item_name


async def get_market_data(server_name: str, item_name: str, hq=False) -> str:
    async with aiohttp.ClientSession() as client:
        try:
            new_item_name, item_id = await get_item_id(
                item_name=item_name, client=client, name_lang="cn"
            )
            if item_id < 0:
                item_name = item_name.replace("_", " ")
                name_lang = ""
                for lang in ["ja", "fr", "de"]:
                    if item_name.endswith(f"|{lang}"):
                        item_name = item_name.replace(f"|{lang}", "")
                        name_lang = lang
                        break
                new_item_name, item_id = await get_item_id(item_name, client, name_lang)
            if item_id < 0:
                return f'所查询物品"{item_name}"不存在'
        except (asyncio.TimeoutError, RetryError):
            logger.error(f"获取物品ID异常：{traceback.format_exc()}")
            return "获取物品ID超时...或许相关api网络出现了问题...请稍后重试..."
        url = f"https://universalis.app/api/{server_name}/{item_id}"
        try:
            r = await client.get(url, timeout=10)
        except asyncio.TimeoutError:
            return "请求universalis.app时发生超时，或许...物价网炸了"
        if r.status != 200:
            if r.status == 404:
                msg = "请确认所查询物品可交易且不可在NPC处购买"
            else:
                logger.warning(
                    f"访问universalis.app时发生错误 (code {r.status}):\n{await r.text()}"
                )
                msg = f"访问universalis.app时发生错误，错误码：{r.status}"
            return msg
        data = await r.json()
    msg = f"{server_name} 的 {new_item_name}{'(HQ)' if hq else ''} 数据如下：\n"
    listing_cnt = 0
    for listing in data["listings"]:
        if hq and not listing["hq"]:
            continue
        retainer_name = listing["retainerName"]
        if "dcName" in data:
            retainer_name += f"({localize_world_name(listing['worldName'])})"
        msg += f"{listing['pricePerUnit']:,}x{listing['quantity']} = {listing['total']:,} {'HQ' if listing['hq'] else '  '} {retainer_name}\n"
        listing_cnt += 1
        if listing_cnt >= 10:
            break
    last_upload_time = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(data["lastUploadTime"] / 1000)
    )
    msg += f"更新时间:{last_upload_time}"
    if listing_cnt == 0:
        msg = "未查询到数据，请使用/market upload命令查看如何上报数据"
    return msg
