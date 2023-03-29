import re
import asyncio
from typing import Tuple

from nonebot.log import logger
from nonebot_plugin_htmlrender.browser import get_new_page
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from .utils import parser_manager

pattern_weibo_com = re.compile(r"https://weibo.com/[0-9]+/([a-zA-Z0-9]+)")
pattern_share_api = re.compile(r"weibo_id=([a-zA-Z0-9]+)")

@parser_manager(
    task_name="url_parse_weibo_parse",
    startswith=(
        "https://share.api.weibo.cn",
        "https://m.weibo.cn",
        "https://weibo.com",
    ),
    ttl=240,
)
async def get_weibo_info(url: str) -> Tuple[Message, str]:
    if url.startswith("https://weibo.com/"):
        if res := pattern_weibo_com.search(url):
            url = f"https://m.weibo.cn/detail/{res.group(1)}"
        else:
            raise Exception(f"Error Weibo Url: {url}")
    elif url.startswith("https://share.api.weibo.cn"):
        if res := pattern_share_api.search(url):
            url = f"https://m.weibo.cn/detail/{res.group(1)}"
        else:
            raise Exception(f"Error Weibo Url: {url}")
    img = None
    for _ in range(5):
        try:
            async with get_new_page(
                is_mobile=True, viewport={"width": 2048, "height": 2732}
            ) as page:
                await page.goto(url)
                # await page.wait_for_selector(".ad-wrap", state="attached", timeout=8 * 1000)
                # await page.eval_on_selector(
                #     selector=".ad-wrap",
                #     expression="(el) => el.style.display = 'none'",
                # )
                # 去除“小程序看微博热搜”横幅
                card = await page.wait_for_selector(
                    f"xpath=//div[@class='card m-panel card9 f-weibo']",
                    timeout=6 * 1000,
                )
                try:
                    await card.wait_for_selector(".wrap", state="attached", timeout=30)
                    await card.eval_on_selector(
                        selector=".wrap",
                        expression="(el) => el.style.display = 'none'",
                    )
                except Exception:
                    pass
                img = await card.screenshot()
                break
        except Exception as e:
            logger.warning(f"截取微博主页失败: {e}")
            await asyncio.sleep(0.5)
    if not img:
        raise Exception("截取微博主页失败")
    return MessageSegment.image(img), url
