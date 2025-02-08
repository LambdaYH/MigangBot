import asyncio
from urllib.parse import unquote, urlparse
from typing import Any, Dict, Iterable, Optional

import anyio
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core.models import UserProperty


async def _local_to_bytes(path: str) -> bytes:
    async with await anyio.open_file(unquote(urlparse(path).path), "rb") as f:
        return await f.read()


async def _gen_new_seg(type_: str, path: str) -> MessageSegment:
    if type_ == "image":
        return MessageSegment.image(await _local_to_bytes(path=path))
    elif type_ == "record":
        return MessageSegment.record(await _local_to_bytes(path=path))


async def _replace_res(
    raw_message: Message, index: int, type_: str, data: MessageSegment
) -> None:
    raw_message[index] = await _gen_new_seg(type_, data["file"])


# 当content为MessageSegment时替换整个content
async def _replace_node(node: MessageSegment, data: MessageSegment) -> None:
    node.data["content"] = await _gen_new_seg(data.type, data.data["file"])


def _is_need_process(seg: MessageSegment) -> bool:
    return (seg.type == "image" or seg.type == "record") and (
        seg.data.get("file") or ""
    ).startswith("file")


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
        if isinstance(data["message"], MessageSegment):
            if _is_need_process(data["message"]):
                data["message"] = await _gen_new_seg(
                    data["message"].type, data["message"].data["file"]
                )
        elif isinstance(data["message"], str):
            pass
        else:
            await asyncio.gather(
                *[
                    _replace_res(data["message"], i, seg.type, seg.data)
                    for i, seg in enumerate(data["message"])
                    if _is_need_process(seg)
                ]
            )
    elif (
        api == "send_forward_msg"
        or api == "send_group_forward_msg"
        or api == "send_private_forward_msg"
    ):
        tasks = []
        for msg in data["messages"]:
            if isinstance(msg, dict):
                content = msg.get("data")["content"]
            else:
                content = msg.data["content"]
            if isinstance(content, MessageSegment) and _is_need_process(content):
                tasks.append(_replace_node(msg, content))
            elif not isinstance(content, str) and isinstance(content, Iterable):
                tasks += [
                    _replace_res(content, i, seg.type, seg.data)
                    for i, seg in enumerate(content)
                    if _is_need_process(seg)
                ]
        await asyncio.gather(*tasks)
