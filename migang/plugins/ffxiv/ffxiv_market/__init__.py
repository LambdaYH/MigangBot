from nonebot.plugin import PluginMetadata
from nonebot import on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import Fullmatch, CommandArg

from .data_source import get_market_data, handle_item_name_abbr

__plugin_meta__ = PluginMetadata(
    name="物价查询",
    description="看看狒狒里商品的物价，基于https://universalis.app",
    usage="""
usage：
    数据来源：https://universalis.app
    指令：
        /market item 物品名 猫/鸟/猪/狗
        /mitem 物品名 猫/鸟/猪/狗
        /market upload：查看上传方法
    示例：
        /mitem 无瑕白 猪
""".strip(),
    extra={
        "unique_name": "migang_ffxiv_market",
        "example": "/mitem\n/market item",
        "author": "migang",
        "version": 0.1,
    },
)
__plugin_category__ = "FF14"
__plugin_aliases__ = ["最终幻想14物价查询"]

ffxiv_market = on_command(
    "/market item", aliases={"/mitem", "/查价"}, priority=5, block=True
)

market_help = on_fullmatch(("/market upload", "/market help"), priority=5, block=True)

help_msg = """/market item 物品名 猫/鸟/猪/狗: 查询服务器的物品交易数据
/market upload: 如何上报数据
Powered by https://universalis.app"""

upload_help = """您可以使用以下几种方式上传交易数据：
0.如果您使用咖啡整合的ACT，可以启用抹茶插件中的Universalis集成功能 http://url.cn/a9xaUIKs 
1.如果您使用过国际服的 XIVLauncher，您可以使用国服支持的Dalamud版本 https://url.cn/6L7nD0gF
2.如果您使用过ACT，您可以加载ACT插件 UniversalisPlugin https://url.cn/TEY1QKKV
3.如果您想不依赖于其他程序，您可以使用 UniversalisStandalone https://url.cn/TEY1QKKV
4.如果您使用过Teamcraft客户端，您也可以使用其进行上传
Powered by https://universalis.app"""


@market_help.handle()
async def _(cmd: str = Fullmatch()):
    if cmd == "/market upload":
        await market_help.finish(upload_help)
    if cmd == "/market help":
        await market_help.finish(help_msg)


@ffxiv_market.handle()
async def _(args: Message = CommandArg()):
    args: str = args.extract_plain_text().strip()
    args_split = args.split(" ")
    if not args or len(args_split) < 2:
        await ffxiv_market.finish(f"参数错误！：\n{help_msg}")
    server_name = args_split[-1]
    if server_name in ("陆行鸟", "莫古力", "猫小胖", "豆豆柴"):
        pass
    elif server_name == "鸟":
        server_name = "陆行鸟"
    elif server_name == "猪":
        server_name = "莫古力"
    elif server_name == "猫":
        server_name = "猫小胖"
    elif server_name == "狗":
        server_name = "豆豆柴"

    item_name = " ".join(args_split[:-1])
    hq = "hq" in item_name or "HQ" in item_name
    if hq:
        item_name = item_name.replace("hq", "", 1).replace("HQ", "", 1)
    item_name = handle_item_name_abbr(item_name)
    msg = await get_market_data(server_name, item_name, hq)
    await ffxiv_market.send(msg)
