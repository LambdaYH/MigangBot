import ujson
import aiohttp
from nonebot.log import logger

headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip,deflate,sdch",
    "Accept-Language": "zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": "music.163.com",
    "Referer": "http://music.163.com/search/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) "
    + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 "
    + "Safari/537.36",
    "X-Real-IP": "39.156.69.79",
    "X-Forwarded-For": "39.156.69.79",
}

api_url = "https://music.163.com/api/search/get/web"


async def search_song(s, limit, stype=1, offset=0, total="true"):
    data = {"s": s, "type": stype, "offset": offset, "total": total, "limit": limit}
    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
        resp = await client.post(api_url, data=data, headers=headers, timeout=5)
        return await resp.json(content_type=None)


async def search(keyword: str, result_num: int = 3):
    song_list = []
    try:
        data = await search_song(keyword, result_num)
        if data and data["code"] == 200:
            for item in data["result"]["songs"][:result_num]:
                song_list.append(
                    {
                        "title": item["name"],
                        "id": item["id"],
                        "content": "/".join(
                            [artist["name"] for artist in item["artists"]]
                        ),
                        "type": "163",
                        "source": "网易云音乐",
                    }
                )
    except Exception as e:
        logger.warning(f"获取网易云歌曲失败, 返回数据, 错误信息error={e}")

    return song_list
