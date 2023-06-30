from typing import Union

from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from .data_source import get_data

__plugin_meta__ = PluginMetadata(
    name="最终幻想14时尚品鉴",
    description="看看这周FF14时尚评鉴的作业",
    usage="""
usage：
    数据来源：
        游玩C哩酱(https://www.youwanc.com/)
    指令：
        /nn
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "FF14"

ffxiv_nuannuan = on_fullmatch(
    ("/暖暖", "/nn", "/nuannuan", "、nn", "、nuannuan"), priority=5, block=True
)


@ffxiv_nuannuan.handle()
async def _(bot: Bot, event: Union[GroupMessageEvent, PrivateMessageEvent]):
    nuannuan_image, nuannuan_text = get_data()
    msg_list = [
        MessageSegment.node_custom(
            event.self_id, "暖暖威", "以下数据来自：游玩C攻略站(https://www.youwanc.com/)"
        ),
        MessageSegment.node_custom(
            event.self_id, "暖暖威", MessageSegment.image(nuannuan_image)
        ),
    ]
    for text in nuannuan_text:
        msg_list.append(MessageSegment.node_custom(event.self_id, "暖暖威", text))
    if isinstance(event, GroupMessageEvent):
        await bot.send_forward_msg(group_id=event.group_id, messages=msg_list)
    else:
        await bot.send_forward_msg(user_id=event.user_id, messages=msg_list)
