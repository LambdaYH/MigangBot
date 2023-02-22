import psutil
from pathlib import Path
import aiohttp
from datetime import datetime
from nonebot_plugin_imageutils import BuildImage, text2image
from nonebot_plugin_imageutils.fonts import add_font
from nonebot import get_driver
from nonebot.log import logger

from migang.core import FONT_PATH


@get_driver().on_startup
async def _():
    await add_font("HWZhongSong.ttf", FONT_PATH / "HWZhongSong.ttf")


async def check():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    baidu: int = 200
    google: int = 200
    async with aiohttp.ClientSession() as client:
        try:
            await client.get("https://www.baidu.com/", timeout=2)
        except Exception as e:
            logger.warning(f"无法访问baidu：{e}")
            baidu = 404
        try:
            await client.get("https://www.google.com/", timeout=2)
        except Exception as e:
            logger.warning(f"无法访问google：{e}")
            google = 404

        rst = (
            f'[Time] {str(datetime.now()).split(".")[0]}\n'
            f"-----System-----\n"
            f"[CPU] {cpu}%\n"
            f"[Memory] {memory}%\n"
            f"[Disk] {disk}%\n"
            f"-----Network-----\n"
            f"[Baidu] {baidu}\n"
            f"[Google] {google}\n"
        )
        text_img = text2image(
            rst,
            bg_color=(255, 255, 255, 120),
            fontsize=24,
            fontname="HWZhongSong.ttf",
            padding=(15, 20),
        )
        bk = BuildImage.open(Path(__file__).parent / "image" / "check.jpg").resize(
            (text_img.width + 50, text_img.height + 140)
        )
        bk.paste(text_img, (25, 70), alpha=True)

        return bk.save_png()
