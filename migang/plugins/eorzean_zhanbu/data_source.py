import os
import random
import asyncio
import hashlib
import secrets
from io import BytesIO
from pathlib import Path
from datetime import date, datetime
from typing import List, Tuple, Union, Optional

import aiohttp
from sqlalchemy import select
from pil_utils import BuildImage
from nonebot_plugin_datastore import create_session

from . import zhanbu_config
from .model import EorzeanZhanbuRecorder

BG_PATH = Path(__file__).parent / "image"


def vertical(str_: str) -> str:
    list_ = []
    for s in str_:
        list_.append(s)
    return "\n".join(list_)


def decrement(text: str) -> List[str]:
    length = len(text)
    result = []
    cardinality = 9
    if length > 4 * cardinality:
        return [False]
    numberOfSlices = 1
    while length > cardinality:
        numberOfSlices += 1
        length -= cardinality
    result.append(numberOfSlices)
    # Optimize for two columns
    space = " "
    length = len(text)
    if numberOfSlices == 2:
        if length % 2 == 0:
            # even
            fillIn = space * int(9 - length / 2)
            return [
                numberOfSlices,
                text[: int(length / 2)] + fillIn,
                fillIn + text[int(length / 2) :],
            ]
        else:
            # odd number
            fillIn = space * int(9 - (length + 1) / 2)
            return [
                numberOfSlices,
                text[: int((length + 1) / 2)] + fillIn,
                fillIn + space + text[int((length + 1) / 2) :],
            ]
    for i in range(0, numberOfSlices):
        if i == numberOfSlices - 1 or numberOfSlices == 1:
            result.append(text[i * cardinality :])
        else:
            result.append(text[i * cardinality : (i + 1) * cardinality])
    return result


def draw(
    luck: int, yi: str, ji: str, dye: str, append_msg: str, base_img: Union[Path, str]
) -> BytesIO:
    img = BuildImage.open(base_img).convert("RGBA")
    # draw luck
    img.draw_text(
        xy=(59, 75, 219, 124),
        text=f"{luck}%",
        fill="#F5F5F5",
        fontsize=45,
        max_fontsize=45,
        fontname="Mamelon",
    )

    # draw dye
    img.draw_text(
        xy=(58, 148, 220, 171),
        text=dye,
        fontsize=18,
        fontname="sakura_yingsuti",
        fill="#323232",
    )

    # draw yi, ji, append_msg
    items = {
        "yi": {"font_center": (180, 297), "text": f"宜 {yi}"},
        "ji": {"font_center": (150, 297), "text": f"忌 {ji}"},
        "append_msg": {"font_center": (90, 305), "text": append_msg},
    }
    font_size = 25
    for k, v in items.items():
        image_font_center = v["font_center"]
        result = decrement(v["text"])
        if not result[0]:
            return Exception(f"Unknown error in daily luck({k})")
        textVertical = []
        for i in range(0, result[0]):
            font_height = len(result[i + 1]) * (font_size + 4)
            textVertical = vertical(result[i + 1])
            x = int(
                image_font_center[0]
                + (result[0] - 2) * font_size / 2
                + (result[0] - 1) * 4
                - i * (font_size + 4)
            )
            y = int(image_font_center[1] - font_height / 2)
            img.draw_text(
                xy=(x, y),
                text=textVertical,
                fill="#323232",
                fontname="sakura_yingsuti",
                fontsize=font_size,
            )
    return img.save_png()


def get_basemap(occupation: str) -> str:
    occupation_path = BG_PATH / occupation
    random_img = secrets.choice(os.listdir(occupation_path))
    return f"{occupation}/{random_img}"


async def get_hitokoto() -> str:
    try:
        async with aiohttp.ClientSession() as client:
            r = await client.get(
                "https://v1.hitokoto.cn/?encode=text&max_length=16&c=d&c=e&c=i&c=k",
                timeout=5,
            )
            text = await r.text()
    except Exception:
        text = "......( )"
    return text


async def get_luck_num(QID: int) -> int:
    QID = float(QID)
    today = date.today()
    formatted_today = int(today.strftime("%y%m%d"))
    strnum = f"{formatted_today * (QID +(secrets.randbelow(1001)/10000 - 0.05))}"
    md5 = hashlib.md5()
    md5.update(strnum.encode("utf-8"))
    res = md5.hexdigest()
    random.seed(res)

    # # 2024 new year update
    if today == date(2024, 2, 10):
        if random.random() < 0.1:
            return 2024
        luck_num = random.randint(0, 100)
        if luck_num < 50:
            luck_num += 50
        return luck_num
    # 2024 new year update end

    return random.randint(0, 100)


def get_luck_num_event(QID: int, event: str) -> str:
    QID = float(QID)
    today = date.today()
    formatted_today = int(today.strftime("%y%m%d"))
    strnum = f"{len(event) * formatted_today}{formatted_today * QID}{event}"
    md5 = hashlib.md5()
    md5.update(strnum.encode("utf-8"))
    res = md5.hexdigest()
    random.seed(res)
    randnum = random.randint(0, 100)
    comment = ""
    if randnum <= 20:
        comment = "大凶"
    elif randnum <= 40:
        comment = "凶"
    elif randnum <= 60:
        comment = "小吉"
    elif randnum <= 80:
        comment = "中吉"
    else:
        comment = "大吉"
    return randnum, comment


def get_event_zhanbu(user_id: int, event: str) -> str:
    random_num, comment = get_luck_num_event(user_id, event)
    return f"""
占卜[{event}]:
    {comment}({random_num})
    """.strip()


async def get_zhanbu_result(user_id: int) -> Tuple[int, str, str, str, str, str]:
    luck = await get_luck_num(user_id)
    luck_occupation = secrets.choice(zhanbu_config.occupation)
    luck_dye = secrets.choice(zhanbu_config.dye)
    luck_yi = secrets.choice(zhanbu_config.event)
    luck_ji = secrets.choice(zhanbu_config.event)
    while luck_yi == luck_ji:
        luck_ji = secrets.choice(zhanbu_config.event)

    if luck_yi == "诸事皆宜":
        luck_ji = "无"
    elif luck_ji == "诸事皆宜":
        luck_ji = "无"
        luck_yi = "诸事皆宜"

    append_msg = ""
    if luck == 100:
        append_msg = "是欧皇中的欧皇！"
    elif luck == 0:
        append_msg = "非极必欧！"
    elif luck > 94:
        append_msg = "是欧皇哦~"
    elif luck < 6:
        append_msg = "是非酋呢~"
    elif luck_occupation == "舞者" and luck >= 50:
        append_msg = f"最佳舞伴->{secrets.choice(zhanbu_config.occupation)}"
    elif (
        zhanbu_config.luck_yi_reply.get(luck_yi) != None
        and zhanbu_config.luck_ji_reply.get(luck_ji) != None
    ):
        if secrets.choice([0, 1]) == 0:
            append_msg += secrets.choice(zhanbu_config.luck_yi_reply.get(luck_yi))
        else:
            append_msg += secrets.choice(zhanbu_config.luck_ji_reply.get(luck_ji))
    elif zhanbu_config.luck_yi_reply.get(luck_yi) != None:
        append_msg += secrets.choice(zhanbu_config.luck_yi_reply.get(luck_yi))
    elif zhanbu_config.luck_ji_reply.get(luck_ji) != None:
        append_msg += secrets.choice(zhanbu_config.luck_ji_reply.get(luck_ji))
    else:
        append_msg = f'"{await get_hitokoto()}"'

    return luck, luck_yi, luck_ji, luck_dye, append_msg, luck_occupation


async def get_eorzean_zhanbu(user_id: int) -> BytesIO:
    async with create_session() as session:
        user: Optional[EorzeanZhanbuRecorder] = await session.scalar(
            statement=select(EorzeanZhanbuRecorder).where(
                EorzeanZhanbuRecorder.user_id == user_id
            )
        )
        if not user or user.time.date() != datetime.now().date():
            luck, yi, ji, dye, append_msg, occupation = await get_zhanbu_result(
                user_id=user_id
            )
            basemap = get_basemap(occupation=occupation)
            if user:
                (
                    user.luck,
                    user.yi,
                    user.ji,
                    user.dye,
                    user.append_msg,
                    user.basemap,
                    user.time,
                ) = (luck, yi, ji, dye, append_msg, basemap, datetime.now())
            else:
                user = EorzeanZhanbuRecorder(
                    user_id=user_id,
                    luck=luck,
                    yi=yi,
                    ji=ji,
                    dye=dye,
                    append_msg=append_msg,
                    basemap=basemap,
                )
                session.add(user)
            await session.commit()
        else:
            luck, yi, ji, dye, append_msg, basemap = (
                user.luck,
                user.yi,
                user.ji,
                user.dye,
                user.append_msg,
                user.basemap,
            )
    return await asyncio.get_event_loop().run_in_executor(
        None, draw, luck, yi, ji, dye, append_msg, BG_PATH / basemap
    )
