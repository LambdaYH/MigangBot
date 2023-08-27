from nonebot import require
from nonebot.params import Depends
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_chatrecorder")
require("nonebot_plugin_datastore")
require("nonebot_plugin_saa")
require("nonebot_plugin_alconna")
require("nonebot_plugin_wordcloud")
require("nonebot_plugin_cesaa")
import nonebot_plugin_saa as saa
from nonebot_plugin_datastore.db import post_db_init
from nonebot_plugin_wordcloud.config import plugin_config
from nonebot_plugin_wordcloud import (
    ensure_group,
    admin_permission,
    get_time_fromisoformat_with_timezone,
)
from nonebot_plugin_alconna import (
    Args,
    Match,
    Query,
    Option,
    Alconna,
    AlconnaQuery,
    on_alconna,
)

from .schedule import schedule_service

post_db_init(schedule_service.update)

__plugin_meta__ = PluginMetadata(
    name="每日热词",
    description="利用群消息生成每日热词+词云",
    usage="""
指令：
    开启热词定时发送 23:59
    关闭热词定时发送
说明：
    调整词云样式请参考词云插件，本插件依赖词云插件生成词云
""".strip(),
)

__plugin_category__ = "订阅"

schedule_cmd = on_alconna(
    Alconna(
        "热词定时发送",
        Option("--action", Args["action_type", ["状态", "开启", "关闭"]], default="状态"),
        Args["type", ["每日"]]["time?", str],
    ),
    permission=admin_permission(),
    use_cmd_start=True,
)
schedule_cmd.shortcut(
    r"热词(?P<type>.+)定时发送状态",
    {
        "prefix": True,
        "command": "热词定时发送",
        "args": ["--action", "状态", "{type}"],
    },
)
schedule_cmd.shortcut(
    r"(?P<action>.+)热词(?P<type>.+)定时发送",
    {
        "prefix": True,
        "command": "热词定时发送",
        "args": ["--action", "{action}", "{type}"],
    },
)


@schedule_cmd.handle(parameterless=[Depends(ensure_group)])
async def _(
    time: Match[str],
    action_type: Query[str] = AlconnaQuery("action.action_type.value", "状态"),
    target: saa.PlatformTarget = Depends(saa.get_target),
):
    if action_type.result == "状态":
        schedule_time = await schedule_service.get_schedule(target)
        await schedule_cmd.finish(
            f"热词每日定时发送已开启，发送时间为：{schedule_time}" if schedule_time else "热词每日定时发送未开启"
        )
    elif action_type.result == "开启":
        schedule_time = None
        if time.available:
            if time_str := time.result:
                try:
                    schedule_time = get_time_fromisoformat_with_timezone(time_str)
                except ValueError:
                    await schedule_cmd.finish("请输入正确的时间，不然我没法理解呢！")
        await schedule_service.add_schedule(target, time=schedule_time)
        await schedule_cmd.finish(
            f"已开启热词每日定时发送，发送时间为：{schedule_time}"
            if schedule_time
            else f"已开启热词每日定时发送，发送时间为：{plugin_config.wordcloud_default_schedule_time}"
        )
    elif action_type.result == "关闭":
        await schedule_service.remove_schedule(target)
        await schedule_cmd.finish("已关闭热词每日定时发送")
