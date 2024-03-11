import aiohttp
from nonebot.log import logger

from migang.core import get_config, post_init_manager

BAIDU_AK = ""
BASE_API = "https://api.map.baidu.com/place/v2/search"


@post_init_manager
async def init():
    global BAIDU_AK
    BAIDU_AK = await get_config("baidumap_ak")


async def get_location(query: str, tag: str, region: str) -> str:
    params = {
        "query": query,
        "tag": tag if tag else "",
        "region": region if region else "中国",
        "output": "json",
        "ak": BAIDU_AK,
    }
    async with aiohttp.ClientSession() as session:
        r = await session.get(BASE_API, params=params)
        rjson = await r.json(content_type=None)
        data = rjson.get("results")
        if (
            rjson["status"] != 0
            or data is None
            or len(data) == 0
            or data[0].get("address") is None
        ):
            logger.warning(f"调用百度地图检索API失败：{rjson}")
            raise Exception("查询地点失败")
        return data[0]["address"]
