import asyncio
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

import anyio
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core.models import UserProperty


async def _local_to_bytes(path: str) -> bytes:
    async with await anyio.open_file(unquote(urlparse(path).path), "rb") as f:
        return await f.read()


async def _replace_res(
    raw_message: Message, index: int, type: str, data: MessageSegment
) -> None:
    if type == "image":
        raw_message[index] = MessageSegment.image(await _local_to_bytes(data["file"]))
    elif type == "record":
        raw_message[index] = MessageSegment.record(await _local_to_bytes(data["file"]))


@Bot.on_called_api
async def handle_api_result(
    bot: Bot,
    exception: Optional[Exception],
    api: str,
    data: Dict[str, Any],
    result: Any,
):
    # 将昵称用昵称系统替换，保留群员卡片
    if (
        (api == "get_group_member_info" or api == "get_stranger_info")
        and (
            name := await UserProperty.filter(user_id=data["user_id"])
            .first()
            .values_list("nickname")
        )
        and (name[0] is not None)
    ):
        result["nickname"] = name[0]


@Bot.on_calling_api
async def _(
    bot: Bot,
    api: str,
    data: Dict[str, Any],
):
    # 将本地文件转换成byte后发出
    if api == "send_msg" or api == "send_group_msg" or api == "send_private_msg":
        await asyncio.gather(
            *[
                _replace_res(data["message"], i, seg.type, seg.data)
                for i, seg in enumerate(data["message"])
                if (seg.type == "image" or seg.type == "record")
                and seg.data["file"].startswith("file")
            ]
        )
    elif (
        api == "send_forward_msg"
        or api == "send_group_forward_msg"
        or api == "send_private_forward_msg"
    ):
        tasks = []
        for msg in data["messages"]:
            tasks += [
                _replace_res(msg.data["content"], i, seg.type, seg.data)
                for i, seg in enumerate(msg.data["content"])
                if (seg.type == "image" or seg.type == "record")
                and seg.data["file"].startswith("file")
            ]
        await asyncio.gather(*tasks)
