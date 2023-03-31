import urllib.parse

import aiohttp
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment


async def get_wolframalpha_simple(input_: str, appid: str):
    params = {"input": input_, "appid": appid}
    url = "https://api.wolframalpha.com/v2/simple"

    try:
        async with aiohttp.ClientSession() as client:
            resp = await client.get(url, params=params, timeout=10)
            if resp.status == 501:
                return "wolframalpha无法理解你的问题..."
            return MessageSegment.image(await resp.read())
    except Exception as e:
        logger.warning(f"Error in get_wolframalpha_simple({input}): {e}")
        return None
