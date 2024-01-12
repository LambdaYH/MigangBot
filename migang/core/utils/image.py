import base64
from io import BytesIO
from pathlib import Path
from typing import Optional

import anyio
import aiohttp
from PIL import Image
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


def pic_to_bytes(pic: Image) -> bytes:
    with BytesIO() as buf:
        pic.save(buf, format="PNG")
        return buf.getvalue()


def pic_to_b64(pic: Image) -> str:
    base64_str = base64.b64encode(pic_to_bytes(pic)).decode()
    return "base64://" + base64_str


async def image_file_to_bytes(file: Path | str) -> bytes:
    async with await anyio.open_file(file, "rb") as f:
        return await f.read()
