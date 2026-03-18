import random
from pathlib import Path
from datetime import timedelta
from typing import List, Optional

import anyio
import ujson
from nonebot import get_driver
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupMessageEvent

from migang.core.permission import BLACK
from migang.core.utils import http_utils
from migang.core.models import ChatGPTChatHistory
from migang.core.manager import permission_manager

from .utils import serialize_message
from .config import sync_get_agent_config
from .dialog_window import dialog_window_manager

ASSET_PATH = Path(__file__).parent / "image"

hello_img = [file for file in (ASSET_PATH / "zai").iterdir()]
hello_msg = set(
    [
        "你好啊",
        "你好",
        "在吗",
        "在不在",
        "您好",
        "您好啊",
        "你好",
        "在",
    ]
)
dialog_window_minutes: int = int(
    sync_get_agent_config("dialog_window_minutes", default_value=10) or 10
)


async def hello(
    nickname: str,
    plain_text: str,
    event: GroupMessageEvent,
    bot: Bot,
) -> Optional[Message]:
    """
    一些打招呼的内容
    """
    if plain_text and plain_text not in hello_msg:
        return None
    dialog_window_manager.refresh(event, dialog_window_minutes)
    logger.info(
        f"hello 命中，已进入连续对话窗口 | group={event.group_id} | duration={dialog_window_minutes}min"
    )
    result = random.choice(
        (
            "哦豁？！",
            "你好！Ov<",
            f"库库库，呼唤{nickname}做什么呢",
            "我在呢！",
            "呼呼，叫俺干嘛",
        )
    )
    reply_message = Message(result) + MessageSegment.image(random.choice(hello_img))
    await ChatGPTChatHistory(
        user_id=event.user_id,
        group_id=event.group_id,
        target_id=event.self_id,
        message=await serialize_message(event.message, bot=bot),
        is_bot=False,
    ).save()
    return reply_message


# 没有回答时回复内容
no_result_img = [file for file in (ASSET_PATH / "no_result").iterdir()]


def no_result(nickname: str) -> Message:
    """
    没有回答时的回复
    """
    return random.choice(
        [
            "你在说啥子？",
            f"纯洁的{nickname}没听懂",
            "下次再告诉你(下次一定)",
            "你觉得我听懂了吗？嗯？",
            "我！不！知！道！",
        ]
    ) + MessageSegment.image(random.choice(no_result_img))


antiinsult: List[str] = []


@get_driver().on_startup
async def _():
    global antiinsult
    data_dir = Path() / "data" / "chat"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / "curse.json"
    try:
        r = await http_utils.request_gh(
            "https://raw.githubusercontent.com/tkgs0/nonebot-plugin-antiinsult/main/nonebot_plugin_antiinsult/curse.json"
        )
        antiinsult = r.json()["curse"]
        async with await anyio.open_file(file_path, "w", encoding="utf8") as f:
            await f.write(ujson.dumps(antiinsult, ensure_ascii=True))
    except Exception as e:
        logger.warning(f"更新反嘴臭词失败：{e}，尝试加载已有数据")
        if file_path.exists():
            async with await anyio.open_file(file_path, "r", encoding="utf8") as f:
                antiinsult = ujson.loads(await f.read())


def anti_zuichou(plain_text: str, user_id: int):
    for word in antiinsult:
        if word in plain_text:
            permission_manager.set_user_perm(
                user_id=user_id, permission=BLACK, duration=timedelta(hours=1)
            )
            return "¿（触发违禁词，拉黑1h）"
