from typing import Optional

import aiohttp
from nonebot.log import logger
from async_lru import alru_cache


@alru_cache(maxsize=32)
async def get_user_avatar(qq: int, size: int = 160) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as client:
            return await (
                await client.get(f"http://q1.qlogo.cn/g?b=qq&nk={qq}&s={size}")
            ).read()
    except Exception as e:
        logger.warning(f"获取用户头像失败 {e}")
        return None
