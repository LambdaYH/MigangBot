from time import time

import psutil
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot import on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment

from .data_source import check

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="自检",
    description="检查所在服务器状态",
    usage="""
usage：
    签到，数据以用户为单位
    指令：
        /ping
        自检（仅超级用户可用）
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)


self_check = on_fullmatch(
    "自检", rule=to_me(), permission=SUPERUSER, block=True, priority=1
)

ping = on_command("/ping", aliases={"、ping"}, block=True, priority=1)


@self_check.handle()
async def _():
    await self_check.send(MessageSegment.image(await check()))


def cpu_status():
    cpu_percent = psutil.cpu_percent()
    msg = f"[CPU] 使用率：{cpu_percent:0.1f}%"
    return msg


@ping.handle()
async def _(event: MessageEvent):
    latency = f"[延迟] {time() - event.time:0.2f}s"
    await ping.finish(f"[MigangBot]\n{cpu_status()}\n{latency}")
