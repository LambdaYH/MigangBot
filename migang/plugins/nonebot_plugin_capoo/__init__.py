import os
import random
import asyncio
from io import BytesIO

from httpx import AsyncClient
from nonebot.log import logger
from nonebot.params import Arg
from nonebot import get_driver, get_plugin_config
from nonebot.plugin import PluginMetadata, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    GROUP,
    GROUP_ADMIN,
    GROUP_OWNER,
    Message,
    ActionFailed,
    MessageSegment,
)

from .config import Config, capoo_path, capoo_pic2, capoo_pic2_path
from .download import (
    hashlib,
    sqlite3,
    check_md5,
    capoo_filename,
    capoo_list_len,
    check_resources,
)

__plugin_meta__ = PluginMetadata(
    name="猫猫虫图片发送",
    description="发送capoo指令后bot会随机发出一张capoo的可爱表情包",
    usage="使用命令：capoo",
    type="application",
    homepage="https://github.com/HuParry/nonebot-plugin-capoo",
    config=Config,
    supported_adapters={"nonebot.adapters.onebot.v11"},
)
capoo_config = get_plugin_config(Config)
capoo_download = capoo_config.capoo_download

driver = get_driver()


@driver.on_startup
async def _():
    if capoo_download:
        logger.info("配置项选择了本地存储图片，正在检查资源文件...")
        asyncio.create_task(check_resources())
    else:
        logger.info("配置项未选择本地存储图片，将通过url发送图片")


picture = on_fullmatch("capoo", permission=GROUP, priority=1, block=True)


@picture.handle()
async def pic():
    if capoo_download:
        conn = sqlite3.connect(capoo_path / "md5.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Picture (
                md5 TEXT PRIMARY KEY,
                img_url TEXT
            )
        """
        )
        cursor.execute("SELECT * FROM Picture ORDER BY RANDOM() limit 1")
        status = cursor.fetchone()
        if status is None:
            await picture.finish("当前还没有图片!")
        file_name = status[1]
        img = capoo_path / file_name
        try:
            await picture.send(MessageSegment.image(img))
        except ActionFailed:
            await picture.send(f"capoo出不来了，稍后再试试吧~")
    else:
        async with AsyncClient() as client:
            resp = await client.get(
                f"https://git.acwing.com/HuParry/capoo/-/raw/master/capoo ({random.randint(1, capoo_list_len)}).gif",
                timeout=5.0,
            )
        picbytes = BytesIO(resp.content).getvalue()
        try:
            await picture.send(MessageSegment.image(picbytes))
        except:
            await picture.send("capoo出不来了，稍后再试试吧~")


def reply_rule():
    return capoo_download


add = on_fullmatch(
    "添加capoo",
    rule=reply_rule,
    permission=GROUP_ADMIN | GROUP_OWNER,
    priority=1,
    block=True,
)


@add.got("pic", prompt="请发送图片！")
async def add_pic(pic_list: Message = Arg("pic")):
    conn = sqlite3.connect(capoo_path / "md5.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Picture (
            md5 TEXT PRIMARY KEY,
            img_url TEXT
        )
    """
    )

    for pic in pic_list:
        if pic.type != "image":
            await add.send(
                pic + MessageSegment.text("\n输入格式有误，请重新触发指令！"),
                at_sender=True,
            )
            continue
        pic_url = pic.data["url"]

        async with AsyncClient() as client:
            resp = await client.get(pic_url, timeout=5.0)

        try:
            resp.raise_for_status()
        except ActionFailed:
            await add.send(pic + MessageSegment.text("\n保存出错了，这张请重试"))
            continue

        data = resp.content
        fmd5 = hashlib.md5(data).hexdigest()

        capoo_cur_picnum = len(os.listdir(str(capoo_pic2_path)))
        if not check_md5(
            conn,
            cursor,
            fmd5,
            f"{capoo_pic2}/{capoo_filename.format(index=str(capoo_cur_picnum + 1))}",
        ):
            await add.send(pic + Message("\n这张已经有了，不能重复添加！"))
        else:
            capoo_cur_picnum = capoo_cur_picnum + 1
            file_name = capoo_filename.format(index=str(capoo_cur_picnum))
            file_path = capoo_pic2_path / file_name

            with file_path.open("wb") as f:
                f.write(data)
            await add.send(pic + Message("\n导入成功！"), at_sender=True)
