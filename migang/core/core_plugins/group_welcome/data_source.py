import asyncio
import hashlib
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
import aiofiles
from pydantic import TypeAdapter
from nonebot.adapters.onebot.v11 import Message, MessageSegment

data_dir = Path("data/group_welcome")
data_dir.mkdir(parents=True, exist_ok=True)


# https://github.com/noneplugin/nonebot-plugin-chatrecorder
async def cache_file(msg: Message):
    async with aiohttp.ClientSession() as client:
        await asyncio.gather(
            *[cache_image_url(seg, client) for seg in msg if seg.type == "image"]
        )


async def cache_image_url(seg: MessageSegment, client: aiohttp.ClientSession):
    if url := seg.data.get("url"):
        for _ in range(3):
            try:
                r = await client.get(url)
                data = await r.read()
                break
            except asyncio.TimeoutException:
                await asyncio.sleep(0.5)
        seg.type = "cached_image"
    else:
        return
    hash_ = hashlib.md5(data).hexdigest()
    filename = f"{hash_}.cache"
    cache_file_path = data_dir / filename
    cache_files = [f.name for f in data_dir.iterdir() if f.is_file()]
    if filename not in cache_files:
        async with aiofiles.open(cache_file_path, "wb") as f:
            await f.write(data)
    seg.data = {"file": filename}


async def serialize_message(message: Message) -> List[Dict[str, Any]]:
    await cache_file(message)
    return [seg.__dict__ for seg in message]


def deserialize_message(message: List[Dict[str, Any]]) -> Message:
    for seg in message:
        if seg["type"] == "cached_image":
            seg["type"] = "image"
            seg["data"]["file"] = (data_dir / seg["data"]["file"]).resolve().as_uri()
    return TypeAdapter(Message).validate_python(message)
