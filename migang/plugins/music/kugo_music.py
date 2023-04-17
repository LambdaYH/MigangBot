import aiohttp
from nonebot.log import logger


async def search(keyword: str, result_num: int = 3):
    search_url = "http://mobilecdn.kugou.com/api/v3/search/song"
    params = {
        "format": "json",
        "keyword": keyword,
        "showtype": 1,
        "page": 1,
        "pagesize": 1,
    }
    song_list = []
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(search_url, params=params)
            result = await resp.json(content_type=None)
            if songs := result["data"]["info"][:result_num]:
                for song in songs:
                    try:
                        hash_ = song["hash"]
                        album_id = song["album_id"]
                        song_url = "http://m.kugou.com/app/i/getSongInfo.php"
                        params = {"cmd": "playInfo", "hash": hash_}
                        resp = await client.get(song_url, params=params)

                        if info := await resp.json(content_type=None):
                            song_list.append(
                                {
                                    "url": f"https://www.kugou.com/song/#hash={hash_}&album_id={album_id}",
                                    "audio": info["url"],
                                    "title": info["songName"],
                                    "content": info["author_name"],
                                    "image": str(info["imgUrl"]).format(size=240),
                                    "type": "custom",
                                    "subtype": "kugo",
                                    "source": "酷狗音乐",
                                }
                            )
                    except Exception as e:
                        logger.warning(f"酷狗音乐详情解析错误：{e}")
                        pass
    except Exception as e:
        logger.warning(f"Kugo music error: {e}")
    return song_list
