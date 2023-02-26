from typing import Tuple

import ujson
import aiohttp
from thefuzz import fuzz


async def get_nbnhhsh(keyword: str) -> Tuple[str, str, str]:
    url = "https://lab.magiconch.com/api/nbnhhsh/guess"
    headers = {"referer": "https://lab.magiconch.com/nbnhhsh/"}
    data = {"text": keyword}
    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
        resp = await client.post(url=url, headers=headers, json=data, timeout=5)
        res = await resp.json()
    title = ""
    result = []
    for i in res:
        if "trans" in i:
            if i["trans"]:
                title = i["name"]
                result.append(f"{i['name']} => {'，'.join(i['trans'])}")
    result = "\n".join(result)
    if fuzz.ratio(title.lower(), keyword.lower()) < 90:
        return "", "", ""
    return title, result, None
