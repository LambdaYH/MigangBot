from pathlib import Path
from datetime import datetime

import psutil
import aiohttp
from nonebot.log import logger
from pil_utils import BuildImage, text2image


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
            font_size=24,
            font_families=["STZhongsong"],
            padding=(15, 20),
        )
        bk = BuildImage.open(Path(__file__).parent / "image" / "check.jpg").resize(
            (text_img.width + 50, text_img.height + 140)
        )
        bk.paste(text_img, (25, 70), alpha=True)

        return bk.save_png()
