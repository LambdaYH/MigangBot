import re
import base64
import hashlib
import mimetypes
from pathlib import Path
from functools import cache
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote, urlparse

import anyio
import httpx
from aiocache import cached
from nonebot.log import logger
from langchain_core.messages import BaseMessage, messages_to_dict, messages_from_dict
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    ActionFailed,
    MessageSegment,
    GroupMessageEvent,
)

from migang.core.models import ChatGPTChatHistory

DIRECT_OUTPUT_MARKERS = (
    "已成功调用该工具，工具结果已直接提供给用户，请勿再次调用",
    "插件已触发，结果已直接发送给用户",
)
IMAGE_CACHE_DIR = Path("data/chat_agent/image_cache")
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@cache
def get_bot_name(bot: Bot) -> str:
    return list(bot.config.nickname)[0]


@cached(ttl=20 * 60)
async def get_user_name(bot: Bot, group_id: int, user_id: int) -> str:
    """获取用户昵称，缓存20分钟

    Args:
        bot (Bot): _description_
        group_id (int): _description_
        user_id (int): _description_

    Returns:
        str: _description_
    """
    if user_id == int(bot.self_id):
        return get_bot_name(bot)
    try:
        user_info = await bot.get_group_member_info(
            group_id=group_id, user_id=user_id, no_cache=False
        )
        user_name = user_info.get("card") or user_info["nickname"]
        return user_name
    except ActionFailed:
        return "未知"


async def _read_local_bytes(path: str) -> bytes:
    async with await anyio.open_file(unquote(urlparse(path).path), "rb") as f:
        return await f.read()


def _guess_image_extension(source: str, mime_type: str) -> str:
    extension = Path(urlparse(source).path or source).suffix
    if extension:
        return extension
    guessed = mimetypes.guess_extension(mime_type or "")
    return guessed or ".png"


async def _cache_image_bytes(
    data: bytes,
    source: str,
    mime_type: str = "image/png",
) -> str:
    digest = hashlib.md5(data).hexdigest()
    extension = _guess_image_extension(source, mime_type)
    cache_path = IMAGE_CACHE_DIR / f"{digest}{extension}"
    if not cache_path.exists():
        async with await anyio.open_file(cache_path, "wb") as f:
            await f.write(data)
    return cache_path.resolve().as_uri()


async def _resolve_image_file_uri(seg: MessageSegment, bot: Bot | None = None) -> str:
    file_value = str(seg.data.get("file") or "").strip()
    url_value = str(seg.data.get("url") or "").strip()

    if file_value.startswith("file://"):
        return file_value
    if file_value and Path(file_value).exists():
        return Path(file_value).resolve().as_uri()
    if url_value.startswith("file://"):
        return url_value

    if bot and file_value and "://" not in file_value:
        try:
            image_info = await bot.get_image(file=file_value)
        except Exception as e:
            logger.debug(f"获取 OneBot 图片文件失败: {e}")
        else:
            local_path = str(image_info.get("file") or "").strip()
            if local_path and Path(local_path).exists():
                return Path(local_path).resolve().as_uri()

    if url_value:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url_value)
                response.raise_for_status()
                mime_type = response.headers.get("content-type", "image/png").split(
                    ";"
                )[0]
                return await _cache_image_bytes(response.content, url_value, mime_type)
        except Exception as e:
            logger.debug(f"缓存图片 URL 失败: {e}")

    return ""


def _coerce_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _truncate_preview(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _extract_sender_value(sender: Any, key: str) -> Any:
    if sender is None:
        return None
    if isinstance(sender, dict):
        return sender.get(key)
    return getattr(sender, key, None)


async def _build_reply_context(
    reply: Any,
    bot: Bot | None = None,
    depth: int = 1,
) -> Dict[str, Any]:
    if reply is None:
        return {}

    context: dict[str, Any] = {}
    message_id = getattr(reply, "message_id", None)
    if message_id is not None:
        context["message_id"] = message_id

    sender = getattr(reply, "sender", None)
    if (user_id := _coerce_int(_extract_sender_value(sender, "user_id"))) is not None:
        context["user_id"] = user_id

    user_name = str(
        _extract_sender_value(sender, "card")
        or _extract_sender_value(sender, "nickname")
        or ""
    ).strip()
    if user_name:
        context["user_name"] = user_name

    reply_message = getattr(reply, "message", None)
    if reply_message:
        context["message"] = await serialize_message(
            reply_message,
            bot=bot,
            depth=depth,
        )
    return context


async def _ensure_reply_segment(
    serialized: List[Dict[str, Any]],
    event: GroupMessageEvent | None,
    bot: Bot | None,
    depth: int,
) -> List[Dict[str, Any]]:
    if event is None or getattr(event, "reply", None) is None:
        return serialized
    if any(seg.get("type") == "reply" for seg in serialized if isinstance(seg, dict)):
        return serialized

    reply_data: dict[str, Any] = {}
    message_id = getattr(event.reply, "message_id", None)
    if message_id is not None:
        reply_data["id"] = message_id
    if depth <= 1:
        reply_data.update(await _build_reply_context(event.reply, bot, depth + 1))
    return [{"type": "reply", "data": reply_data}, *serialized]


async def _reply_segment_to_text(
    seg: MessageSegment,
    group_id: int,
    bot: Bot,
) -> str:
    data = seg.data if isinstance(seg.data, dict) else {}
    quoted_text = ""
    quoted_message = data.get("message")
    if isinstance(quoted_message, list):
        try:
            quoted_text = await uniform_message(
                deserialize_message(quoted_message),
                group_id=group_id,
                bot=bot,
                include_reply_context=False,
            )
        except Exception as e:
            logger.debug(f"解析引用消息内容失败: {e}")

    if not quoted_text:
        quoted_text = str(data.get("text") or "").strip()

    user_name = str(data.get("user_name") or "").strip()
    if (
        not user_name
        and (user_id := _coerce_int(data.get("user_id") or data.get("qq"))) is not None
    ):
        try:
            user_name = await get_user_name(bot=bot, group_id=group_id, user_id=user_id)
        except Exception as e:
            logger.debug(f"获取引用消息发送者昵称失败: {e}")

    user_name = user_name or "某人"
    if quoted_text:
        return f"[引用 {user_name}: {_truncate_preview(quoted_text)}] "

    message_id = data.get("message_id") or data.get("id")
    if message_id:
        return f"[引用 {user_name} 的消息#{message_id}] "
    return f"[引用 {user_name} 的一条消息] "


async def serialize_message(
    message: Message | str,
    bot: Bot | None = None,
    event: GroupMessageEvent | None = None,
    depth: int = 0,
) -> List[Dict[str, Any]]:
    if isinstance(message, str):
        message = Message(message)
    serialized: list[dict[str, Any]] = []
    for seg in message:
        if seg.type == "text" or seg.type == "at":
            serialized.append(seg.__dict__)
            continue
        if seg.type == "reply":
            reply_data = dict(seg.data)
            if depth <= 1:
                reply_data.update(
                    await _build_reply_context(
                        getattr(event, "reply", None),
                        bot,
                        depth + 1,
                    )
                )
            serialized.append({"type": "reply", "data": reply_data})
            continue
        if seg.type != "image":
            continue
        image_data = dict(seg.data)
        if file_uri := await _resolve_image_file_uri(seg, bot):
            image_data["file"] = file_uri
        serialized.append({"type": "image", "data": image_data})
    return await _ensure_reply_segment(serialized, event=event, bot=bot, depth=depth)


def deserialize_message(message: List[Dict[str, Any]]) -> Message:
    deserialized = Message()
    for seg in message:
        if not isinstance(seg, dict):
            continue
        seg_type = str(seg.get("type") or "").strip()
        if not seg_type:
            continue
        seg_data = seg.get("data") or {}
        if not isinstance(seg_data, dict):
            seg_data = {}
        deserialized.append(MessageSegment(seg_type, seg_data))
    return deserialized


def serialize_langchain_messages(messages: List[BaseMessage]) -> Dict[str, Any]:
    return {
        "storage_type": "langchain_messages",
        "messages": messages_to_dict(messages),
    }


def deserialize_langchain_messages(payload: Dict[str, Any]) -> List[BaseMessage]:
    return messages_from_dict(payload.get("messages", []))


def is_langchain_message_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("storage_type") == "langchain_messages"
        and isinstance(payload.get("messages"), list)
    )


def message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
                continue
            if not isinstance(block, dict):
                continue
            if "text" in block and isinstance(block["text"], str):
                parts.append(block["text"])
            elif block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return str(content or "")


def has_direct_output_marker(messages: List[BaseMessage]) -> bool:
    for message in messages:
        content = message_content_to_text(getattr(message, "content", ""))
        if any(marker in content for marker in DIRECT_OUTPUT_MARKERS):
            return True
    return False


def strip_think_tags(text: str) -> str:
    without_think = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return without_think.strip()


async def _uniform_message_impl(
    message: Message,
    group_id: int,
    bot: Bot,
    include_reply_context: bool,
) -> str:
    msg = ""
    for seg in message:
        if seg.is_text():
            msg += seg.data.get("text", "")
        elif seg.type == "reply":
            if include_reply_context:
                msg += await _reply_segment_to_text(seg, group_id=group_id, bot=bot)
        elif seg.type == "at":
            qq = seg.data.get("qq", None)
            if qq:
                if qq == "all":
                    msg += "@全体成员"
                elif qq == bot.self_id:
                    msg += f"@{get_bot_name(bot)}"
                else:
                    user_name = await get_user_name(
                        bot=bot, group_id=group_id, user_id=int(qq)
                    )
                    if user_name:
                        msg += f"@{user_name}"  # 保持给bot看到的内容与真实用户看到的一致
        elif seg.type == "image":
            msg += "[图片]"
    return msg


async def uniform_message(
    message: Message,
    group_id: int,
    bot: Bot,
    include_reply_context: bool = True,
) -> str:
    return await _uniform_message_impl(
        message=message,
        group_id=group_id,
        bot=bot,
        include_reply_context=include_reply_context,
    )


async def image_segment_to_model_block(
    seg: MessageSegment,
    bot: Bot | None = None,
) -> Dict[str, Any] | None:
    file_uri = str(seg.data.get("file") or "").strip()
    url_value = str(seg.data.get("url") or "").strip()

    if not file_uri or not file_uri.startswith("file://"):
        file_uri = await _resolve_image_file_uri(seg, bot)
    if file_uri.startswith("file://"):
        try:
            image_bytes = await _read_local_bytes(file_uri)
        except Exception as e:
            logger.debug(f"读取图片缓存失败: {e}")
        else:
            mime_type = mimetypes.guess_type(file_uri)[0] or "image/png"
            encoded = base64.b64encode(image_bytes).decode("ascii")
            logger.info(
                f"图片已转为 base64 发送给模型: mime={mime_type} | bytes={len(image_bytes)}"
            )
            return {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
            }

    if url_value:
        logger.info("图片无法读取本地文件，回退为远程 URL 发送给模型")
        return {"type": "image_url", "image_url": {"url": url_value}}
    return None


async def message_to_model_content(
    message: Message,
    group_id: int,
    bot: Bot,
    prefix_text: str = "",
    include_reply_context: bool = True,
) -> str | List[Dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    def append_text(text: str) -> None:
        if not text:
            return
        if blocks and blocks[-1].get("type") == "text":
            blocks[-1]["text"] += text
        else:
            blocks.append({"type": "text", "text": text})

    append_text(prefix_text)

    for seg in message:
        if seg.is_text():
            append_text(seg.data.get("text", ""))
        elif seg.type == "reply":
            if include_reply_context:
                append_text(
                    await _reply_segment_to_text(seg, group_id=group_id, bot=bot)
                )
        elif seg.type == "at":
            qq = seg.data.get("qq", None)
            if not qq:
                continue
            if qq == "all":
                append_text("@全体成员")
            elif qq == bot.self_id:
                append_text(f"@{get_bot_name(bot)}")
            else:
                user_name = await get_user_name(
                    bot=bot, group_id=group_id, user_id=int(qq)
                )
                append_text(f"@{user_name}" if user_name else "@用户")
        elif seg.type == "image":
            image_block = await image_segment_to_model_block(seg, bot)
            if image_block is not None:
                blocks.append(image_block)
            else:
                append_text("[图片]")

    if not blocks:
        return prefix_text.strip()
    if len(blocks) == 1 and blocks[0].get("type") == "text":
        return blocks[0]["text"]
    return blocks


async def gen_chat_text(
    event: GroupMessageEvent,
    bot: Bot,
    include_reply_context: bool = False,
) -> Tuple[str, bool]:
    """生成合适的会话消息内容(eg. 将cq at 解析为真实的名字)"""
    wake_up = False
    for seg in event.message:
        if seg.type == "at" and seg.data["qq"] == "all":
            wake_up = True
            break
    normalized_message = deserialize_message(
        await serialize_message(event.message, bot=bot, event=event)
    )
    return (
        await uniform_message(
            message=normalized_message,
            group_id=event.group_id,
            bot=bot,
            include_reply_context=include_reply_context,
        ),
        wake_up,
    )


def is_reply_to_bot(event: GroupMessageEvent, bot: Bot) -> bool:
    reply = getattr(event, "reply", None)
    if reply is None:
        return False
    sender = getattr(reply, "sender", None)
    reply_user_id = _coerce_int(_extract_sender_value(sender, "user_id"))
    return reply_user_id is not None and str(reply_user_id) == str(bot.self_id)


async def gen_chat_line(chat_history: ChatGPTChatHistory, bot: Bot) -> str:
    return f"[{chat_history.time.astimezone().strftime('%H:%M:%S %p')}] {await get_user_name(group_id=chat_history.group_id,user_id=chat_history.user_id, bot=bot)}: {await uniform_message(deserialize_message(chat_history.message), group_id=chat_history.group_id, bot=bot)}"
