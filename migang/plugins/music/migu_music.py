import aiohttp
from nonebot.log import logger

USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1"
headers = {"referer": "https://m.music.migu.cn/v3", "User-Agent": USER_AGENT}


async def search(keyword, result_num: int = 3):
    """搜索音乐"""
    song_list = []
    # ?rows=20&type=2&keyword=霜雪千年&pgc=1
    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                url=f"https://m.music.migu.cn/migu/remoting/scr_search_tag?rows=20&type=2&keyword={keyword}&pgc=1",
                headers=headers,
                timeout=5,
            )
            res_data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning(f"Request Migu Music Timeout {e}")
        return []
    try:
        for item in res_data["musics"][:result_num]:
            song_list.append(
                {
                    "url": "https://music.migu.cn/v3/music/song/" + item["copyrightId"],
                    "audio": item["mp3"],
                    "image": item["cover"],
                    "title": item["songName"],
                    "content": item["singerName"],
                    "type": "custom",
                    "subtype": "migu",
                    "source": "咪咕音乐",
                }
            )
    except Exception as e:
        logger.info(f"No MIGU music find of {keyword}:{e}")

    return song_list
