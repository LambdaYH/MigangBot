import os
import random
import re

import ujson as json

from migang.core import get_config

from .utils import ai_message_manager

url = "http://openapi.tuling123.com/openapi/api/v2"


async def get_chat_result(text: str, img_url: str, user_id: int, nickname: str) -> str:
    """
    获取 AI 返回值，顺序： 特殊回复 -> 图灵 -> 青云客
    :param text: 问题
    :param img_url: 图片链接
    :param user_id: 用户id
    :param nickname: 用户昵称
    :return: 回答
    """
    global index
    ai_message_manager.add_message(user_id, text)
    special_rst = await ai_message_manager.get_result(user_id, nickname)
    if special_rst:
        ai_message_manager.add_result(user_id, special_rst)
        return special_rst
    rst = await tu_ling(text, img_url, user_id)
    if not rst:
        return no_result()
    if nickname:
        if len(nickname) < 5:
            if random.random() < 0.5:
                nickname = "~".join(nickname) + "~"
                if random.random() < 0.2:
                    if nickname.find("大人") == -1:
                        nickname += "大~人~"
        rst = str(rst).replace("小主人", nickname).replace("小朋友", nickname)
    ai_message_manager.add_result(user_id, rst)
    return rst


# 图灵接口
async def tu_ling(text: str, img_url: str, user_id: int) -> str:
    """
    获取图灵接口的回复
    :param text: 问题
    :param img_url: 图片链接
    :param user_id: 用户id
    :return: 图灵回复
    """
    global index
    TL_KEY = await get_config("turing_key")
    req = None
    if not TL_KEY:
        return ""
    try:
        if text:
            req = {
                "perception": {
                    "inputText": {"text": text},
                    "selfInfo": {
                        "location": {"city": "陨石坑", "province": "火星", "street": "第5坑位"}
                    },
                },
                "userInfo": {"apiKey": TL_KEY[index], "userId": str(user_id)},
            }
        elif img_url:
            req = {
                "reqType": 1,
                "perception": {
                    "inputImage": {"url": img_url},
                    "selfInfo": {
                        "location": {"city": "陨石坑", "province": "火星", "street": "第5坑位"}
                    },
                },
                "userInfo": {"apiKey": TL_KEY[index], "userId": str(user_id)},
            }
    except IndexError:
        index = 0
        return ""
    text = ""
    response = await AsyncHttpx.post(url, json=req)
    if response.status_code != 200:
        return no_result()
    resp_payload = json.loads(response.text)
    if int(resp_payload["intent"]["code"]) in [4003]:
        return ""
    if resp_payload["results"]:
        for result in resp_payload["results"]:
            if result["resultType"] == "text":
                text = result["values"]["text"]
                if "请求次数超过" in text:
                    text = ""
    return text


def hello() -> str:
    """
    一些打招呼的内容
    """
    result = random.choice(
        (
            "哦豁？！",
            "你好！Ov<",
            f"库库库，呼唤{NICKNAME}做什么呢",
            "我在呢！",
            "呼呼，叫俺干嘛",
        )
    )
    img = random.choice(os.listdir(IMAGE_PATH / "zai"))
    if img[-4:] == ".gif":
        result += image(IMAGE_PATH / "zai" / img)
    else:
        result += image(IMAGE_PATH / "zai" / img)
    return result


# 没有回答时回复内容
def no_result() -> str:
    """
    没有回答时的回复
    """
    return random.choice(
        [
            "你在说啥子？",
            f"纯洁的{NICKNAME}没听懂",
            "下次再告诉你(下次一定)",
            "你觉得我听懂了吗？嗯？",
            "我！不！知！道！",
        ]
    ) + image(
        IMAGE_PATH / "noresult" / random.choice(os.listdir(IMAGE_PATH / "noresult"))
    )


async def check_text(text: str) -> str:
    """
    ALAPI文本检测，主要针对青云客API，检测为恶俗文本改为无回复的回答
    :param text: 回复
    """
    if not Config.get_config("alapi", "ALAPI_TOKEN"):
        return text
    params = {"token": Config.get_config("alapi", "ALAPI_TOKEN"), "text": text}
    try:
        data = (await AsyncHttpx.get(check_url, timeout=2, params=params)).json()
        if data["code"] == 200:
            if data["data"]["conclusion_type"] == 2:
                return ""
    except Exception as e:
        logger.error(f"检测违规文本错误...{type(e)}：{e}")
    return text
