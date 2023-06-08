from typing import Tuple

import ujson
import aiohttp

from migang.core import get_config

api_url = "https://api.a20safe.com/api.php"


async def get_baidu(keyword: str) -> Tuple[str, str, str]:
    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
        r = await client.get(
            api_url,
            params={
                "api": 21,
                "key": await get_config("baidubaike_key"),
                "text": keyword,
            },
        )
        r = await r.json()
        if (
            r["code"] == 0
            and r["data"][0]["content"] != "词条不存在"
            and r["data"][0]["content"].strip() != ""
        ):
            return keyword, r["data"][0]["content"], None

    return "", "", None
