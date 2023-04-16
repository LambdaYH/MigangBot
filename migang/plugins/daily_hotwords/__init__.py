from typing import Tuple, Union, cast

from nonebot.adapters import Message
from nonebot import require, on_command
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.params import Command, CommandArg
from nonebot.adapters.onebot.v11 import Bot as BotV11
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import ChannelMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupMessageEventV11
from nonebot.adapters.onebot.v12 import GroupMessageEvent as GroupMessageEventV12

require("nonebot_plugin_datastore")
require("nonebot_plugin_wordcloud")
from nonebot_plugin_datastore.db import post_db_init
from nonebot_plugin_wordcloud.config import plugin_config
from nonebot_plugin_wordcloud.utils import get_time_fromisoformat_with_timezone

from .schedule import schedule_service

post_db_init(schedule_service.update)

__plugin_meta__ = PluginMetadata(
    name="每日热词",
    description="利用群消息生成每日热词+词云",
    usage="""
指令：
    开启热词每日定时发送 23:59
    关闭热词每日定时发送
说明：
    调整词云样式请参考词云插件，本插件依赖词云插件生成词云
""".strip(),
)

schedule_cmd = on_command(
    "热词每日定时发送状态",
    aliases={"开启热词每日定时发送", "关闭热词每日定时发送"},
    permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN,
)

__plugin_category__ = "订阅"


@schedule_cmd.handle()
async def _(
    bot: Union[BotV11, BotV12],
    event: Union[GroupMessageEventV11, GroupMessageEventV12, ChannelMessageEvent],
    commands: Tuple[str, ...] = Command(),
    args: Message = CommandArg(),
):
    command = commands[0]

    group_id = ""
    guild_id = ""
    channel_id = ""
    if isinstance(event, GroupMessageEventV11):
        group_id = str(event.group_id)
        platform = "qq"
    elif isinstance(event, GroupMessageEventV12):
        bot = cast(BotV12, bot)
        group_id = event.group_id
        platform = bot.platform
    else:
        bot = cast(BotV12, bot)
        guild_id = event.guild_id
        channel_id = event.channel_id
        platform = bot.platform

    if command == "热词每日定时发送状态":
        schedule_time = await schedule_service.get_schedule(
            bot.self_id,
            platform,
            group_id=group_id,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        if schedule_time:
            await schedule_cmd.finish(f"热词每日定时发送已开启，发送时间为：{schedule_time}")
        else:
            await schedule_cmd.finish("热词每日定时发送未开启")
    elif command == "开启热词每日定时发送":
        schedule_time = None
        if time_str := args.extract_plain_text():
            try:
                schedule_time = get_time_fromisoformat_with_timezone(time_str)
            except ValueError:
                await schedule_cmd.finish("请输入正确的时间，不然我没法理解呢！")
        await schedule_service.add_schedule(
            bot.self_id,
            platform,
            time=schedule_time,
            group_id=group_id,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        if schedule_time:
            await schedule_cmd.finish(f"已开启热词每日定时发送，发送时间为：{schedule_time}")
        else:
            await schedule_cmd.finish(
                f"已开启热词每日定时发送，发送时间为：{plugin_config.wordcloud_default_schedule_time}"
            )
    elif command == "关闭热词每日定时发送":
        await schedule_service.remove_schedule(
            bot.self_id,
            platform,
            group_id=group_id,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        await schedule_cmd.finish("已关闭热词每日定时发送")
