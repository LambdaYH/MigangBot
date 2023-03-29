from pathlib import Path
import time
from typing import Optional
from datetime import datetime, timedelta

from nonebot import require
from nonebot.log import logger
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageSegment

from nonebot.permission import SUPERUSER
from migang.core import DATA_PATH

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_new_page

__plugin_meta__ = PluginMetadata(
    name="今日素材",
    description="看看原神今天要刷什么",
    usage="""
usage：
    看看原神今天要刷什么
    指令：
        今日素材/今天素材
""".strip(),
    extra={
        "unique_name": "migang_gushi",
        "example": "",
        "author": "HibiKier",
        "version": 0.1,
    },
)

__plugin_category__ = "原神相关"


material = on_fullmatch("今日素材", priority=5, block=True)

super_cmd = on_fullmatch("更新原神今日素材", permission=SUPERUSER, priority=1, block=True)

IMAGE_PATH = DATA_PATH / "migang_genshin" / "material_remind"
IMAGE_PATH.mkdir(exist_ok=True, parents=True)


@material.handle()
async def _():
    if time.strftime("%w") == "0":
        await material.send("今天是周日，所有材料副本都开放了。")
        return
    img = await update_image()
    await material.send(MessageSegment.image(img) + "\n※ 每日素材数据来源于米游社")


@super_cmd.handle()
async def _():
    if await update_image():
        await super_cmd.send("更新成功...")
        logger.info(f"更新每日天赋素材成功...")
    else:
        await super_cmd.send(f"更新失败...")


async def update_image() -> Optional[Path]:
    try:
        path = IMAGE_PATH / f"{(datetime.now() - timedelta(hours=4)).date()}.png"
        if path.exists():
            return path
        async with get_new_page(viewport={"width": 860, "height": 3000}) as page:
            url = "https://bbs.mihoyo.com/ys/obc/channel/map/193"
            await page.goto(url)
            await page.wait_for_timeout(3000)
            await page.locator(
                '//*[@id="__layout"]/div/div[2]/div[2]/div/div[1]/div[2]/div/div'
            ).screenshot(path=path)
            return path
    except Exception as e:
        logger.error(f"原神每日素材更新出错...: {e}")
        return None
