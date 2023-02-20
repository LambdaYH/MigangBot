import random
from asyncio.exceptions import TimeoutError
from pathlib import Path
from typing import Optional

import aiohttp
import ujson
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.log import logger

from migang.core import get_config


async def get_turing(msg: Message, user_id: int) -> Optional[str]:
    """
    获取 AI 返回值，顺序： 特殊回复 -> 图灵 -> 青云客
    :param text: 问题
    :param img_url: 图片链接
    :param user_id: 用户id
    :param nickname: 用户昵称
    :return: 回答
    """
    text = "".join([seg.data["text"] for seg in msg["text"]])
    img_url = [seg.data["url"] for seg in msg["image"]]
    img_url = img_url[0] if img_url else ""
    rst = await tu_ling(text, img_url, user_id)
    if not rst:
        return None
    rst = str(rst).replace("小主人", "{nickname}").replace("小朋友", "{nickname}")
    return rst


# 图灵接口
turing_key_idx = 0


async def tu_ling(text: str, img_url: str, user_id: int) -> Optional[str]:
    """
    获取图灵接口的回复
    :param text: 问题
    :param img_url: 图片链接
    :param user_id: 用户id
    :return: 图灵回复
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
    except TimeoutError as e:
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


def hello(msg: Message, user_id: int) -> Optional[Message]:
    """
    一些打招呼的内容
    """
    text = "".join([seg.data["text"] for seg in msg["text"]])
    if text not in hello_msg:
        return None
    result = random.choice(
        (
            "哦豁？！",
            "你好！Ov<",
            "库库库，呼唤{nickname}做什么呢",
            "我在呢！",
            "呼呼，叫俺干嘛",
        )
    )
    return result + MessageSegment.image(random.choice(hello_img))


# 没有回答时回复内容
no_result_img = [
    file for file in (Path(__file__).parent / "image" / "no_result").iterdir()
]


def no_result(msg: Message, user_id: int) -> Message:
    """
    没有回答时的回复
    """
    return random.choice(
        [
            "你在说啥子？",
            "纯洁的{nickname}没听懂",
            "下次再告诉你(下次一定)",
            "你觉得我听懂了吗？嗯？",
            "我！不！知！道！",
        ]
    ) + MessageSegment.image(random.choice(no_result_img))
