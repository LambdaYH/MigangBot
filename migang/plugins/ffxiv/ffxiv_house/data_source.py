import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import aiohttp
from nonebot import require

from .const import (
    me,
    pe,
    ue,
    area,
    servers,
    area_rev,
    comments,
    area_alias,
    house_size,
    region_type,
    lottery_stage,
    house_size_alt,
    l_sl_available,
    region_type_rev,
    l_sl_unavailable,
    l_sl_resultsperiod,
)

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import template_to_pic

# https://house.ffxiv.cyou/#/about
api_url = "https://house.ffxiv.cyou/api/sales"

user_agent = (
    "MigangBot(https://github.com/LambdaYH/MigangBot) / LambdaYH <cinte@cinte.cc>"
)

template_path = Path(__file__).parent / "template"


def get_area_name(area_id: int) -> str:
    return area_rev[area_id]


def get_area_id(area_name: int) -> int:
    if area_name in area_alias:
        area_name = area_alias[area_name]
    return area.get(area_name)


def get_size_name(size_id: int) -> str:
    return house_size_alt[size_id]


def lottery_end_time(house: Dict[str, Any]) -> str:
    return (
        time.strftime("%m-%d %H:%M", time.localtime(house["EndTime"]))
        if house["EndTime"]
        else time.strftime("%m-%d %H:%M")
    )


def get_update_time(house: Dict[str, Any]) -> str:
    return time.strftime(
        "%m-%d %H:%M:%S",
        time.localtime(
            house["UpdateTime"] if house["UpdateTime"] else house["LastSeen"]
        ),
    )


def get_region_type(house: Dict[str, Any]) -> str:
    return region_type[house["RegionType"]]


def get_server_id(server_name: str) -> int:
    return servers.get(server_name)


def get_comment(house: Dict[str, Any]) -> str:
    return comments[house["Area"]][house["ID"] - 1]


def get_house_size_id(size: str) -> int:
    return house_size.get(size.upper())


def get_region_type_id(region_name: str) -> int:
    return region_type_rev.get(region_name)


def fix_lottery_info(house: Dict[str, Any]):
    a = int(time.time())
    # if (!e.EndTime || !e.UpdateTime || void 0 === e.Winner || !e.State || void 0 === e.Participate)
    if (
        house["EndTime"] == 0
        or house["UpdateTime"] == 0
        or (house.get("Winner") is None)
        or house["State"] == 0
        or (house.get("Participate") is None)
    ):
        s_endtime = int(
            time.mktime(
                time.strptime("2022-08-08 23:00:00+0800", "%Y-%m-%d %H:%M:%S%z")
            )
        )
        i = s_endtime
        while i > (house["FirstSeen"] + pe):
            i -= pe
        while i < house["FirstSeen"]:
            i += pe
        if a < i:
            house["EndTime"] = i
            house["State"] = l_sl_unavailable
        else:
            while a > (i + pe):
                i += pe
            if a < (i + me):
                house["EndTime"] = i + me
                house["State"] = l_sl_available
            else:
                house["EndTime"] = i + pe
                house["State"] = l_sl_resultsperiod
        return
    if a >= house["EndTime"]:
        s = house["EndTime"]
        i = house["State"]
        while s and a >= s:
            if i == l_sl_available:
                s += ue
                i = l_sl_resultsperiod
            elif i == l_sl_resultsperiod or i == l_sl_unavailable:
                if i == l_sl_resultsperiod:
                    house["Participate"] = -1
                    house["Winner"] = -1
                    house["UpdateTime"] = -1
                s += me
                i = l_sl_available
        house["EndTime"] = s
        house["State"] = i


def lottery_has_participate(house: Dict[str, Any]) -> bool:
    return house["State"] != 0 and (
        house["State"] == l_sl_available
        or house["State"] == l_sl_resultsperiod
        and 0 != house["Participate"]
    )


def lottery_is_prepareing(house: Dict[str, Any]) -> bool:
    return house["State"] != 0 and house["State"] == l_sl_unavailable


def lottery_has_winner(house: Dict[str, Any]) -> bool:
    return house["State"] != 0 and house["State"] == l_sl_resultsperiod


async def get_server_house_info(server_id: int) -> List[Dict[str, Any]]:
    async with aiohttp.ClientSession() as client:
        r = await client.get(
            api_url, params={"server": server_id}, headers={"User-Agent": user_agent}
        )
        return await r.json()


async def get_house_info(
    server_id: int,
    area: Literal[-1, 0, 1, 2, 3, 4] = -1,
    house_size: Literal[-1, 0, 1, 2] = -1,
    region: Literal[-1, 1, 2] = -1,
) -> Optional[bytes]:
    server_house_info = await get_server_house_info(server_id=server_id)
    if area != -1:
        server_house_info = [
            house for house in server_house_info if house["Area"] == area
        ]
    if house_size != -1:
        server_house_info = [
            house for house in server_house_info if house["Size"] == house_size
        ]
    if region != -1:
        server_house_info = [
            house for house in server_house_info if house["RegionType"] == region
        ]
    if not server_house_info:
        return None
    server_house_info = sorted(server_house_info, key=lambda v: v["FirstSeen"])
    houses = []
    for house in server_house_info:
        fix_lottery_info(house=house)
        houses.append(
            {
                "area_id": house["Area"],
                "area_name": get_area_name(house["Area"]),
                "size": get_size_name(house["Size"]),
                "location": f"{house['Slot'] + 1} 区 {house['ID']} 号",
                "price": format(house["Price"], ","),
                "comment": get_comment(house),
                "stage": lottery_stage[house["State"]],
                "update_time": get_update_time(house=house),
                "region_type": get_region_type(house=house),
            }
        )
        if (
            house["UpdateTime"]
            and lottery_has_participate(house)
            and house["Participate"] >= 0
            and house["Winner"] == 0
        ):
            houses[-1]["participate"] = f"{house['Participate']} 人预约"
        elif house["UpdateTime"] and lottery_has_winner(house) and house["Winner"] > 0:
            houses[-1]["participate"] = f"{house['Winner']} 号中签"
        elif (
            house["UpdateTime"]
            and lottery_has_winner(house)
            and house["Participate"] == 0
            and house["Winner"] == 0
        ):
            houses[-1]["participate"] = "无人参与"
        elif house["UpdateTime"] <= 0:
            houses[-1]["participate"] = "(推测数据)"

        if house["EndTime"] and (not lottery_is_prepareing(house)):
            houses[-1]["time"] = f"{lottery_end_time(house)} 截止"
        elif house["EndTime"] and lottery_is_prepareing(house):
            houses[-1]["time"] = f"{lottery_end_time(house)} 开始"
    if len(houses) > 80:
        raise TimeoutError
    return await template_to_pic(
        template_path=template_path,
        template_name="house.html",
        templates={"houses": houses},
        pages={
            "viewport": {"width": 1200, "height": 200},
        },
    )
