from pathlib import Path
from typing import Tuple, Optional

import anyio
import aiohttp
from nonebot.log import logger
from async_lru import alru_cache


async def pic_file_to_bytes(pic: Path | str) -> str:
    async with await anyio.open_file(pic, "rb") as f:
        return await f.read()


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


# pillow 10+ 中去除了getSize，以此替代
def getsize(font, text) -> Tuple[int, int]:
    left, top, right, bottom = font.getbbox(text)
    return right - left, bottom - top
