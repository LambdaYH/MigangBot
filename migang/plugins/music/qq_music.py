import aiohttp
from nonebot.log import logger


async def search(keyword, result_num: int = 3):
    """搜索音乐"""
    song_list = []
    params = {
        "word": keyword,
    }
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                url=f"https://api.vkeys.cn/v2/music/tencent",
                params=params,
                timeout=5,
            )
            res_data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning(f"Request QQ Music Timeout: {e}")
        return []
    try:
        for item in res_data["data"][:result_num]:
            song_list.append(
                {
                    "title": item["song"],
                    "id": item["id"],
                    "content": item["singer"],
                    "type": "qq",
                    "source": "QQ音乐",
                }
            )
    except Exception as e:
        logger.info(f"No QQ music find of {keyword}:{e}")

    return song_list
