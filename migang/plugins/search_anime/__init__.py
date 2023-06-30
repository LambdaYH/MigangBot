from nonebot.log import logger
from nonebot import on_startswith
from nonebot.plugin import PluginMetadata
from nonebot.params import Startswith, EventPlainText
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
)

from migang.core import ConfigItem, get_config

from .data_source import from_anime_get_info

__plugin_meta__ = PluginMetadata(
    name="搜番",
    description="找不到想看的动漫吗？",
    usage="""
搜索动漫资源
指令：
    搜番  [番剧名称或者关键词]
示例：
    搜番 命运石之门
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "一些工具"
__plugin_config__ = ConfigItem(
    "max_count", initial_value=10, default_value=10, description="搜索动漫返回的最大数量"
)


search_anime = on_startswith("搜番", priority=5, block=True)


@search_anime.handle()
async def _(
    bot: Bot,
    event: MessageEvent,
    cmd: str = Startswith(),
    plain_text: str = EventPlainText(),
):
    keyword = plain_text.removeprefix(cmd).strip()
    if not keyword:
        await search_anime.finish("请在指令后接上想要搜索的番剧名称哦~")
    await search_anime.send(f"开始搜番 {keyword}，可能有些慢，请稍等", at_sender=True)
    anime_report = await from_anime_get_info(keyword, await get_config("max_count"))
    if anime_report:
        if isinstance(anime_report, str):
            await search_anime.finish(anime_report)
        mes_list = [
            MessageSegment.node_custom(
                user_id=event.self_id, nickname="搜番威", content=mes
            )
            for mes in anime_report
        ]
        if isinstance(event, GroupMessageEvent):
            await bot.send_forward_msg(group_id=event.group_id, messages=mes_list)
        else:
            await bot.send_forward_msg(user_id=event.user_id, messages=mes_list)
    else:
        logger.warning(f"未找到番剧 {keyword}")
        await search_anime.send(f"未找到番剧 {keyword}（也有可能是超时，再尝试一下？）")
