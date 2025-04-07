import re
import math
import traceback
from typing import Any, Set, Dict, List

import anyio
import aiohttp
from nonebot import require
from nonebot.log import logger
from pil_utils import BuildImage, text2image
from tenacity import RetryError, retry, wait_fixed, stop_after_attempt

from migang.core import DATA_PATH
from migang.core.utils import http_utils
from migang.utils.file import async_load_data, async_save_data

from .md_render import md_to_pic

PATH = DATA_PATH / "howtocook"
IMAGE_PATH = PATH / "image"
IMAGE_PATH.mkdir(parents=True, exist_ok=True)
MENU_FILE = PATH / "how_to_cook.json"
MENU_IMAGE = PATH / "menu.jpg"

API_URL = (
    "https://api.github.com/repos/Anduin2017/HowToCook/git/trees/master?recursive=1"
)


async def generate_menu_image(menu: Dict[str, Any]):
    menu_list: List[str] = list(menu)
    col_count = 3
    row_count = math.ceil(len(menu_list) / col_count)
    cols = []
    for i in range(3):
        cols.append("\n".join(menu_list[i * row_count : (i + 1) * row_count]))
    col_imgs = []
    for col in cols:
        col_imgs.append(
            text2image(
                col, bg_color=(240, 240, 240), fontsize=30, fontname="FZSJ-QINGCRJ"
            )
        )
    width = 0
    height = 0
    for img in col_imgs:
        width += img.width
        height = max(height, img.height)
    col_gap = 20
    bg = BuildImage.new(
        "RGB",
        size=(80 + width + col_gap * (len(col_imgs) - 1), 160 + 20 + height),
        color=(240, 240, 240),
    )
    bg.draw_text(
        (0, 0, bg.width, 160),
        text="菜   谱",
        fontname="DFBuDingW12-GB",
        fontsize=60,
        max_fontsize=60,
    )
    start_x = 40
    for img in col_imgs:
        bg.paste(img, (start_x, 160))
        start_x += img.width + col_gap
    async with await anyio.open_file(MENU_IMAGE, "wb") as f:
        await f.write(bg.save_jpg().getvalue())


async def update_menu():
    menu_local = await async_load_data(MENU_FILE)
    if "data" not in menu_local:
        menu_local["data"] = {}

    r = await http_utils.request_gh(API_URL)
    menu_remote = r.json()
    # 有变化才更新
    if "sha" not in menu_local or menu_local["sha"] != menu_remote["sha"]:
        menu_local["sha"] = menu_remote["sha"]
        for item in menu_remote["tree"]:
            path: str = item["path"]
            # 是个菜谱
            if path.startswith("dishes") and path.endswith(".md"):
                name = path.split("/")[-1].removesuffix(".md")
                if (
                    name not in menu_local["data"]
                    or menu_local["data"][name]["sha"] != item["sha"]
                ):

                    @retry(stop=stop_after_attempt(7), wait=wait_fixed(5))
                    async def save():
                        md_text = (
                            await http_utils.request_gh(
                                f"https://raw.githubusercontent.com/Anduin2017/HowToCook/master/{path}"
                            )
                        ).text
                        # 放真实的图片链接
                        prefix_path = "(" + http_utils.get_gh_url(
                            f"https://raw.githubusercontent.com/Anduin2017/HowToCook/master/{'/'.join(path.split('/')[:-1])}/"
                        )
                        md_text = re.sub(
                            r"\(\.\/([\s\S]+?\.(jpg|png|webp|jpeg))\)",
                            prefix_path + r"\1)",
                            md_text,
                        )
                        md_image = await md_to_pic(md_text, width=1000)
                        async with await anyio.open_file(
                            IMAGE_PATH / f"{name}.png", "wb"
                        ) as f:
                            await f.write(md_image)

                    try:
                        await save()
                        menu_local["data"][name] = {"sha": item["sha"]}
                    except RetryError:
                        logger.error(f"{name}的菜单图片下载失败！{traceback.format_exc()}")
        await generate_menu_image(menu_local["data"])
        await async_save_data(menu_local, MENU_FILE)


async def update_menu_set(menu: Set[str]):
    menu.clear()
    data = await async_load_data(MENU_FILE)
    if "data" in data:
        for dish in data["data"]:
            menu.add(dish)


async def update_all(menu: Set[str], need_update_menu: bool = False):
    if need_update_menu:
        await update_menu()
    await update_menu_set(menu=menu)
