import random
from pathlib import Path
from datetime import timedelta
from typing import List, Optional
from asyncio.exceptions import TimeoutError as AsyncioTimeoutError

import anyio
import ujson
import aiohttp
from nonebot import get_driver
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment, GroupMessageEvent

from migang.core import get_config
from migang.core.permission import BLACK
from migang.core.manager import permission_manager


async def get_turing(
    nickname: str, plain_text: str, event: GroupMessageEvent, user_id: int
) -> Optional[str]:
    """获取图灵回复"""
    img_url = [seg.data["url"] for seg in event.message["image"]]
    img_url = img_url[0] if img_url else ""
    rst = await tu_ling(plain_text, img_url, user_id)
    if not rst:
        return None
    rst = rst.replace("小主人", nickname).replace("小朋友", nickname)
    return rst


# 图灵接口
turing_key_idx = 0


async def tu_ling(text: str, img_url: str, user_id: int) -> Optional[str]:
    """
    获取图灵接口的回复
    """
    global turing_key_idx
    tl_keys = await get_config("turing_keys")
    if not tl_keys:
        return None
    tl_key = tl_keys[turing_key_idx]
    req = {
        "perception": {
            "inputText": {"text": text},
            "selfInfo": {
                "location": {"city": "南极洲", "province": "南极洲", "street": "南极火山烹饪研究所"}
            },
        },
        "userInfo": {"apiKey": tl_key, "userId": str(user_id)},
    }
    if text:
        req["perception"]["inputText"] = {"text": text}
    if img_url:
        req["perception"]["inputImage"] = {"url": img_url}
    text = None
    try:
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
            async with client.post(
                url="http://openapi.turingapi.com/openapi/api/v2", json=req, timeout=5
            ) as response:
                if response.status != 200:
                    return None
                resp_payload = await response.json(content_type=None)
    except AsyncioTimeoutError as e:
        logger.warning(f"访问turingapi超时：{e}")
        return None
    if int(resp_payload["intent"]["code"]) in [4003]:
        return ""
    if resp_payload["results"]:
        for result in resp_payload["results"]:
            if result["resultType"] == "text":
                text = result["values"]["text"]
                if "请求次数超过" in text:
                    text = None
                    turing_key_idx = (turing_key_idx + 1) % len(tl_keys)
    return text


hello_img = [file for file in (Path(__file__).parent / "image" / "zai").iterdir()]
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


def hello(nickname: str, plain_text: str) -> Optional[Message]:
    """
    一些打招呼的内容
    """
    if plain_text and plain_text not in hello_msg:
        return None
    result = random.choice(
        (
            "哦豁？！",
            "你好！Ov<",
            f"库库库，呼唤{nickname}做什么呢",
            "我在呢！",
            "呼呼，叫俺干嘛",
        )
    )
    return result + MessageSegment.image(random.choice(hello_img))


# 没有回答时回复内容
no_result_img = [
    file for file in (Path(__file__).parent / "image" / "no_result").iterdir()
]


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
        async with aiohttp.ClientSession() as session:
            r = await session.get(
                "https://raw.githubusercontent.com/tkgs0/nonebot-plugin-antiinsult/main/nonebot_plugin_antiinsult/curse.json",
                timeout=5,
            )
            antiinsult = (await r.json(content_type=None))["curse"]
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
