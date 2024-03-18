from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from nonebot import on_command, on_endswith
from nonebot.params import CommandArg, EventPlainText
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment

from migang.core import ConfigItem

from .data_source import get_location

__plugin_meta__ = PluginMetadata(
    name="地点搜索",
    description="输入地名，返回地址",
    usage="""
usage：
    指令：
        xxx在哪
        地点搜索 城市 xxx
    示例：
        天一广场在哪
        地点搜索 宁波 天一广场
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "一些工具"
__plugin_config__ = ConfigItem(
    key="baidumap_ak",
    description="从 https://lbsyun.baidu.com/faq/api?title=webapi/guide/webservice-placeapi/district 获取",
)


where = on_endswith("在哪", priority=14)
search_location = on_command("地点检索", priority=14)


@where.handle()
async def _(event: MessageEvent, msg: str = EventPlainText()):
    location = msg.rstrip("在哪").strip()
    try:
        address = await get_location(location, None, None)
        await where.send(MessageSegment.reply(event.message_id) + address)
    except Exception as e:
        logger.info(f"主动式地点检索错误：{e}")
        logger.info(f"无法检索地点：{location}。跳过")


@search_location.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    keyword = msg.extract_plain_text()
    params = keyword.split(" ", maxsplit=1)
    region = None
    location = None
    if len(params) == 2:
        region = params[0].strip()
        location = params[1].strip()
    else:
        location = params[0].strip()
    try:
        address = await get_location(location, None, region)
        await search_location.send(MessageSegment.reply(event.message_id) + address)
    except Exception:
        await search_location.send(MessageSegment.reply(event.message_id) + "无法检索到该地点")
