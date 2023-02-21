from typing import Optional

import aiohttp
import ujson
from async_lru import alru_cache
from nonebot.log import logger


@alru_cache(maxsize=16)
async def get_user_avatar(qq: int) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
            return await (
                await client.get(f"http://q1.qlogo.cn/g?b=qq&nk={qq}&s=160")
            ).read()
    except Exception as e:
        logger.warning(f"获取用户头像失败 {e}")
        return None
