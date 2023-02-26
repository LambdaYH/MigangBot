import aiohttp
from nonebot.log import logger


async def search(keyword, result_num: int = 3):
    """搜索音乐"""
    song_list = []
    params = {
        "format": "json",
        "inCharset": "utf-8",
        "outCharset": "utf-8",
        "notice": 0,
        "platform": "yqq.json",
        "needNewCode": 0,
        "uin": 0,
        "hostUin": 0,
        "is_xml": 0,
        "key": keyword,
    }
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                url="https://c.y.qq.com/splcloud/fcgi-bin/smartbox_new.fcg",
                params=params,
                timeout=5,
            )
            res_data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning(f"Request QQ Music Timeout: {e}")
        return []
    try:
        for item in res_data["data"]["song"]["itemlist"][:result_num]:
            song_list.append(
                {
                    "title": item["name"],
                    "id": item["id"],
                    "content": item["singer"],
                    "type": "qq",
                    "source": "QQ音乐",
                }
            )
    except Exception as e:
        logger.info(f"No QQ music find of {keyword}:{e}")

    return song_list
