import urllib.parse
from typing import Annotated

from nonebot.params import CommandArg
from nonebot import require, on_command
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.utils.text import is_number
from migang.core import ConfigItem, get_config

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_new_page

__plugin_meta__ = PluginMetadata(
    name="汇率转换",
    description="快速查询汇率转换",
    usage="""
直接从Google获取的结果
指令：
    汇率转换 from:to 数额
示例：
    汇率转换 usd:cny 5 表示查询5usd转换成的人民币数额
    汇率转换 eur 5
说明：
    当to为空时，默认为cny
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "一些工具"
__plugin_config__ = ConfigItem(
    "proxy", initial_value=None, default_value=None, description="代理服务器"
)


exchange = on_command("汇率转换", priority=5, block=False)


@exchange.handle()
async def _(args: Annotated[Message, CommandArg()]):
    args = args.extract_plain_text().split(" ")
    if len(args) != 2:
        await exchange.finish("格式错误，请按照【汇率转换 from:to 数额】发送")
    from_to = args[0].split(":")
    if len(from_to) == 1:
        from_ = from_to[0]
        to_ = "cny"
    elif len(from_to) == 2:
        from_, to_ = from_to[0], from_to[1]
    else:
        await exchange.finish("输入转换的货币必须为 from:to")
    if not is_number(args[1]):
        await exchange.finish("用于转换的数额必须为数字")
    params = {}
    if proxy := await get_config("proxy"):
        params["proxy"] = {"server": proxy}
    try:
        async with get_new_page(**params) as page:
            await page.goto(
                f"https://www.google.com/search?{urllib.parse.urlencode({'q': f'{args[1]}+{from_}+to+{to_}', 'hl':'zh-cn'})}",
                wait_until="networkidle",
                timeout=10 * 1000,
            )
            card = await page.query_selector(
                "div[data-attrid='Converter']",
            )
            img = await card.screenshot()
    except Exception:
        await exchange.finish("似乎无法实现这种货币的转换呢...试试换个输入吧")
    await exchange.send(MessageSegment.image(img))
