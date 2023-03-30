import random
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

import aiohttp
from aiocache import cached
from nonebot.log import logger
from pil_utils import BuildImage
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.utils.file import async_load_data

logo_path = Path(__file__).parent / "res" / "logo.jpg"


@cached(ttl=600)
async def get_data():
    data = await async_load_data(Path(__file__).parent / "data.json")

    def add(key: str):
        output = {}
        for k, v in data[key].items():
            output[k] = v["id"]
            for nickname in v["nickname"]:
                output[nickname] = v["id"]
        return output

    return add("job"), add("race"), add("sex")


async def search_id(glamour_id: int, client: aiohttp.ClientSession) -> Dict[str, Any]:
    try:
        glamour_url = f"http://api.ffxivsc.cn/glamour/v1/getGlamourInfo?uid=&glamourId={glamour_id}"
        headers = {
            "Host": "api.ffxivsc.cn",
            "Origin": "https://www.ffxivsc.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36",
            "Referer": f"https://www.ffxivsc.cn/page/glamour.html?glamourId={glamour_id}".format(),
            "Accept-Encoding": "gzip, deflate, br",
        }
        r = await (await client.get(glamour_url, headers=headers, timeout=5)).json()
        flag = r["flag"]
        result = {}
        if flag == 200:
            r = r["array"][0]
            result["flag"] = 200
            result["left"] = (
                f'主手：{r.get("glamourWeaponry") or "无"}-{r.get("glamourWeaponryColor") or "无染色"}\n\n\n'
                + f'头部：{r.get("glamourHeadgearColor") or "无染色"}-{r.get("glamourHeadgearColor") or "无染色"}\n\n\n'
                + f'上衣：{r.get("glamourBodygear") or "无"}-{r.get("glamourBodygearColor") or "无染色"}\n\n\n'
                + f'手套：{r.get("glamourHandgear") or "无"}-{r.get("glamourHandgearColor") or "无染色"}\n\n\n'
                + f'腿部：{r.get("glamourLeggear") or "无"}-{r.get("glamourLeggearColor") or "无染色"}\n\n\n'
                + f'脚部：{r.get("glamourFootgear") or "无"}-{r.get("glamourFootgearColor") or "无染色"}'
            )
            result["right"] = (
                f'副手：{r.get("glamourSecond") or "无"}-{r.get("glamourSecondColor") or "无染色"}\n\n\n'
                + f'耳环：{r.get("glamourEarringsgear") or "无"}-{r.get("glamourEarringsgearColor") or "无染色"}\n\n\n'
                + f'项链：{r.get("glamourNecklacegear") or "无"}-{r.get("glamourNecklacegearColor") or "无染色"}\n\n\n'
                + f'手镯：{r.get("glamourArmillaegear") or "无"}-{r.get("glamourArmillaegearColor") or "无染色"}\n\n\n'
                + f'戒指：{r.get("glamourRingLgear") or "无"}-{r.get("glamourRingLgearColor") or "无染色"}\n\n\n'
                + f'戒指：{r.get("glamourRingRgear") or "无"}-{r.get("glamourRingRgearColor") or "无染色"}'
            )
            result["glamour_id"] = glamour_id
            result["race"] = r["glamourCharacter"] + "-" + r["glamourClass"]
            result["title"] = r["glamourTitle"] + f"-ID：{glamour_id}"
            result["introduction"] = r["glamourIntroduction"]
            result["img"] = r["glamourUrl"]
        else:
            result["flag"] = 400
        return result
    except Exception as e:
        logger.warning(f"获取幻化信息失败，id={glamour_id}：{e}")
        return None


async def result_to_img(
    result: Dict[str, Any], client: aiohttp.ClientSession
) -> MessageSegment:
    title = result["title"]
    itd = result["introduction"]
    tmp = list(itd)
    t = 50
    while t < len(tmp):
        tmp.insert(t, "\n")
        t += 50
    itd = "".join(tmp)
    race = result["race"]
    try:
        img = await client.get(result["img"], timeout=15)
        pic_foo = BuildImage.open(BytesIO(await img.read())).resize((521, 1000))
    except asyncio.TimeoutError:
        logger.warning(f"获取封面图{result['img']}超时")
        return f"封面图丢失,请前往原地址查看\nhttps://www.ffxivsc.cn/page/glamour.html?glamourId={result['glamour_id']}"

    logo = BuildImage.open(logo_path)
    bk = BuildImage.new("RGB", (2000, 1000), "white")
    bk.paste(pic_foo)
    bk.paste(logo, (1825, 925))
    bk.draw_text(
        (600, 50),
        title + "\n\n" + itd + "\n\n" + race + "\n\n",
        fontname="HONOR Sans CN",
        fill="black",
        fontsize=28,
    )
    bk.draw_text(
        (596, 254),
        text=result["left"],
        fontname="HONOR Sans CN",
        fill="black",
        fontsize=28,
    )
    bk.draw_text(
        (1386, 254),
        text=result["right"],
        fontname="HONOR Sans CN",
        fill="black",
        fontsize=28,
    )
    return MessageSegment.image(bk.save_png())


async def search_jr(
    job: int,
    race: int,
    sex: int,
    sort: int,
    time: int,
    item_name: str,
    item_flag: bool = False,
) -> MessageSegment:
    async with aiohttp.ClientSession() as client:
        headers = {
            "Host": "api.ffxivsc.cn",
            "Origin": "https://www.ffxivsc.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
            "Referer": "https://www.ffxivsc.cn/page/glamourList.html",
            "Accept-Encoding": "gzip, deflate, br",
        }
        params = {"job": job, "race": race, "sex": sex}
        if item_flag:
            params["itemName"] = item_name
            params["sort"] = 1
            params["time"] = 0
        else:
            params["sort"] = sort
            params["time"] = time
            params["pageNum"] = 1
        try:
            r = await client.get(
                "http://api.ffxivsc.cn/glamour/v1/getLibraryFilterGlamours",
                params=params,
                headers=headers,
                timeout=5,
            )
            r = await r.json()
        except Exception as e:
            logger.warning(f"获取幻化列表失败：{e}")
            return "访问光之收藏家网页异常"
        if r["flag"] == 200:
            i = random.randint(0, len(r["array"]) - 1)
            result = await search_id(r["array"][i]["glamourId"], client)
            img = await result_to_img(result, client)
        else:
            img = "未能筛选到结果，请尝试更改筛选信息，\n职业：{}\n种族：{}\n性别：{}\n装备名称：{}".format(
                job, race, sex, item_name
            )
        return img
