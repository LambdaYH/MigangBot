from io import BytesIO
from typing import List, Optional, Union

import aiohttp
from async_lru import alru_cache
from nonebot import get_driver
from nonebot.log import logger
from nonebot_plugin_imageutils import BuildImage, text2image
from nonebot_plugin_imageutils.fonts import add_font

from migang.core import FONT_PATH
from migang.core.manager.request_manager import FriendRequest, GroupRequest


@get_driver().on_startup
async def _():
    await add_font("HONORSans-Regular.ttf", FONT_PATH / "HONORSans-Regular.ttf")
    await add_font("HYWenHei-85W.ttf", FONT_PATH / "HYWenHei-85W.ttf")
    await add_font("msyh.ttf", FONT_PATH / "msyh.ttf")
    await add_font("yz.ttf", FONT_PATH / "yz.ttf")


@alru_cache(maxsize=16)
async def get_user_avatar(qq: int) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as client:
            return await (
                await client.get(f"http://q1.qlogo.cn/g?b=qq&nk={qq}&s=160")
            ).read()
    except Exception as e:
        logger.warning(f"获取用户头像失败 {e}")
        return None


# zhenxun_bot
async def build_request_img(
    requests: Union[List[FriendRequest], List[GroupRequest]], type_: str
) -> BuildImage:
    imgs: List[BuildImage] = []
    for i, request in enumerate(requests):
        avatar = (
            BuildImage.open(BytesIO(await get_user_avatar(request.user_id)))
            .resize((80, 80))
            .circle()
        )
        age_bk = text2image(
            str(request.age),
            bg_color="#04CAF7" if request.sex == "male" else "#F983C1",
            padding=(3, 1),
            fontname="yz.ttf",
            fontsize=15,
            fallback_fonts=False,
        )
        with BytesIO() as buf:
            age_bk.save(buf, "PNG")
            age_bk = BuildImage.open(buf).circle_corner(5)
        button = text2image(
            text="同意/拒绝",
            bg_color=(238, 239, 244, 254),
            padding=(7, 7),
            fontname="HYWenHei-85W.ttf",
            fontsize=15,
        )
        with BytesIO() as buf:
            button.save(buf, "PNG")
            button = BuildImage.open(buf).circle_corner(10)

        comment = text2image(
            f"对方留言：{request.comment}",
            padding=(0, 0),
            fontsize=12,
            fontname="HONORSans-Regular.ttf",
            fill=(140, 140, 143),
        )
        info = BuildImage.new(mode="RGBA", size=(500, 100), color=(254, 254, 254))
        info.paste(avatar, pos=(15, int((info.height - avatar.height) / 2)), alpha=True)
        info.draw_text(
            (120, 15), request.user_name or "None", fontname="HONORSans-Regular.ttf"
        )
        info.paste(age_bk, (120, 50), True)
        info.paste(comment, (120 + age_bk.width + 10, 49), True)
        if isinstance(request, GroupRequest):
            group_info = text2image(
                text=f"邀请你加入：{request.group_name}({request.group_id})",
                fontsize=12,
                fontname="HONORSans-Regular.ttf",
                fill=(140, 140, 143),
                padding=(0, 0),
            )
            info.paste(group_info, (120, 74), True)
        info.paste(button, (380, 35), True)
        id_img = text2image(
            text=f"id：{i}", fontsize=13, fill=(140, 140, 143), padding=(0, 0)
        )
        info.paste(id_img, (400, 10), True)
        time_img = text2image(
            text=request.time.strftime("%Y-%m-%d %H:%M:%S"),
            padding=(1, 1),
            fill=(140, 140, 143),
            fontname="HONORSans-Regular.ttf",
            fontsize=8,
        )
        info.paste(
            time_img, pos=(info.width - time_img.width, info.height - time_img.height)
        )
        imgs.append(info)

    req_img_comb = BuildImage.new(mode="RGBA", size=(500, len(imgs) * 100))
    for i, img in enumerate(imgs):
        req_img_comb.paste(img, (0, 100 * i))
    bk = BuildImage.new(
        "RGB", (req_img_comb.width, req_img_comb.height + 50), color="#F8F9FB"
    )
    bk.paste(req_img_comb, (0, 50))
    bk.draw_text(
        (15, 13),
        "好友请求" if type_ == "friend" else "入群请求",
        fontsize=20,
        fontname="HONORSans-Regular.ttf",
    )
    return bk