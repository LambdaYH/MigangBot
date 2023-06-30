import asyncio
import datetime

from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot import require, on_command
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.utils.text import is_number

from .data_source import get_wbtop, gen_wbtop_pic

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_new_page

__plugin_meta__ = PluginMetadata(
    name="微博热搜",
    description="刚买完瓜，在吃瓜现场",
    usage="""
usage：
    在QQ上吃个瓜
    指令：
        微博热搜：发送实时热搜
        微博热搜 [id]：截图该热搜页面
        示例：微博热搜 5
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

wbtop = on_command("微博热搜", priority=5, block=True)


wbtop_url = "https://weibo.com/ajax/side/hotSearch"

wbtop_data = []


@wbtop.handle()
async def _(arg: Message = CommandArg()):
    global wbtop_data
    msg = arg.extract_plain_text()
    if wbtop_data:
        now_time = datetime.datetime.now()
        if now_time > wbtop_data["time"] + datetime.timedelta(minutes=5):
            data, code = await get_wbtop(wbtop_url)
            if code != 200:
                await wbtop.finish(data, at_sender=True)
            else:
                wbtop_data = data
    else:
        data, code = await get_wbtop(wbtop_url)
        if code != 200:
            await wbtop.finish(data, at_sender=True)
        else:
            wbtop_data = data

    if not msg:
        img = await asyncio.get_event_loop().run_in_executor(
            None, gen_wbtop_pic, wbtop_data["data"]
        )
        await wbtop.send(img)
    if is_number(msg) and 0 < int(msg) <= 50:
        url = wbtop_data["data"][int(msg) - 1]["url"]
        await wbtop.send("开始截取数据...")
        try:
            async with get_new_page(viewport={"width": 2048, "height": 2732}) as page:
                await page.goto(
                    url,
                    wait_until="networkidle",
                )
                card = await page.wait_for_selector("#pl_feed_main", timeout=30 * 1000)
                img = await card.screenshot()
                await wbtop.send(MessageSegment.image(img))
        except Exception as e:
            logger.warning(f"截取微博发生错误：{e}")
            await wbtop.finish("发生了一些错误.....")
