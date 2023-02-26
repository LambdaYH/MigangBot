import aiohttp
from nonebot.log import logger


async def search(keyword: str, result_num: int = 3):
    search_url = "https://search.kuwo.cn/r.s"
    params = {
        "all": keyword,
        "pn": 0,
        "rn": 1,
        "ft": "music",
        "rformat": "json",
        "encoding": "utf8",
        "pcjson": "1",
        "vipver": "MUSIC_9.1.1.2_BCS2",
    }
    song_list = []
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(search_url, params=params, timeout=5)
            result = await resp.json(content_type=None)
            if songs := result["abslist"][:result_num]:
                for song in songs:
                    try:
                        rid = str(song["MUSICRID"]).strip("MUSIC_")
                        song_url = "http://m.kuwo.cn/newh5/singles/songinfoandlrc"
                        params = {"musicId": rid, "httpsStatus": 1}
                        resp = await client.get(song_url, params=params)
                        result = await resp.json(content_type=None)

                        if info := result["data"]["songinfo"]:
                            play_url = "https://kuwo.cn/api/v1/www/music/playUrl"
                            params = {"mid": rid, "type": "music", "httpsStatus": 1}
                            resp = await client.get(play_url, params=params)
                            result = await resp.json(content_type=None)

                            if data := result["data"]:
                                song_list.append(
                                    {
                                        "url": f"https://kuwo.cn/play_detail/{rid}",
                                        "audio": data["url"],
                                        "title": info["songName"],
                                        "content": info["artist"],
                                        "image": info["pic"],
                                        "type": "custom",
                                        "subtype": "kuwo",
                                        "source": "酷我音乐",
                                    }
                                )
                    except:
                        pass
    except Exception as e:
        logger.warning(f"Kuwo music error: {e}")
    return song_list
