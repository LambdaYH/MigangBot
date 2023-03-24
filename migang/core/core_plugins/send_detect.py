"""检测群内重复回复内容，防止两个bot刷屏，需要在go-cqhttp里开启自身消息上报
"""
import time
import bisect
from typing import Any, Dict

from nonebot import on
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, Event, Message

from migang.core.permission import BLACK
from migang.core.manager import permission_manager, group_manager
from migang.core import ConfigItem, get_config, post_init_manager

__plugin_hidden__ = True
__plugin_always_on__ = True
__plugin_meta__ = PluginMetadata(
    name="发送消息检测_",
    description="防止bot刷屏",
    usage="",
    extra={
        "unique_name": "migang_send_detect",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_config__ = (
    ConfigItem(
        key="repeat_check_on",
        initial_value=True,
        default_value=True,
        description="重复消息发送检测的总开关",
    ),
    ConfigItem(
        key="repeat_limit",
        initial_value=3,
        default_value=3,
        description="连续发送重复消息后禁言的条数",
    ),
    ConfigItem(
        key="repeat_check_duration",
        initial_value=120,
        default_value=120,
        description="在此区间内连续发送n条重复消息就静默",
    ),
    ConfigItem(
        key="repeat_ban_time",
        initial_value=90,
        default_value=90,
        description="检测到区间内连续发送重复消息的静默时间",
    ),
    ConfigItem(
        key="send_on",
        initial_value=True,
        default_value=True,
        description="过于频繁发送消息检测总开关",
    ),
    ConfigItem(
        key="send_limit",
        initial_value=15,
        default_value=15,
        description="时间区间内发送条数的限制",
    ),
    ConfigItem(
        key="send_duration",
        initial_value=60,
        default_value=60,
        description="频繁发送消息检测时间区间",
    ),
    ConfigItem(
        key="send_ban_time",
        initial_value=126,
        default_value=126,
        description="检测到区间内频繁发送消息的静默时间",
    ),
)

repeat_check_on = True
repeat_limit = 3
repeat_check_duration = 2 * 60
repeat_ban_time = 90

send_on = True
send_limit = 15
send_duration = 60
send_ban_time = 126


@post_init_manager
async def _():
    global repeat_check_on, repeat_limit, repeat_check_duration, repeat_ban_time, send_on, send_limit, send_duration, send_ban_time
    repeat_check_on = await get_config("repeat_check_on")
    repeat_limit = await get_config("repeat_limit")
    repeat_check_duration = await get_config("repeat_check_duration")
    repeat_ban_time = await get_config("repeat_ban_time")

    send_on = await get_config("send_on")
    send_limit = await get_config("send_limit")
    send_duration = await get_config("send_duration")
    send_ban_time = await get_config("send_ban_time")


class GroupSelfMessage:
    def __init__(self) -> None:
        self.__data: Dict[int, Dict[str, Any]] = {}

    def __get_group(self, group_id: int) -> Dict[str, Any]:
        group = self.__data.get(group_id)
        if not group:
            group = self.__data[group_id] = {
                "message": None,
                "repeat": 0,
                "time": 0,
                "message_time": [],
            }
        return group

    def check_group_repeat(self, group_id: int, message: Message) -> bool:
        """检查，若返回True，则表明发送重复信息超出次数，准备处理

        Args:
            group_id (int): _description_
            message (Message): _description_

        Returns:
            bool: _description_
        """
        msg_str = str(message)
        group = self.__get_group(group_id=group_id)
        if group["message"] != msg_str or (
            (time.time() - group["time"]) > repeat_check_duration
        ):
            group["message"] = msg_str
            group["repeat"] = 0
            group["time"] = time.time()
        else:
            group["repeat"] += 1
            if group["repeat"] >= repeat_limit - 1:
                return True
        return False

    def check_group_send(self, group_id: int) -> bool:
        group = self.__get_group(group_id=group_id)
        now = time.time()
        group["message_time"].append(now)
        group["message_time"] = group["message_time"][
            bisect.bisect_left(group["message_time"], now - send_duration) :
        ]
        if len(group["message_time"]) >= send_limit:
            return True
        return False


group_self_message = GroupSelfMessage()


def _rule(event) -> bool:
    if not hasattr(event, "group_id"):
        return False
    # 这个类型的hook不到，所以这里加个检测防止自己的消息触发自己
    return group_manager.check_group_plugin_status("send_detect", event.group_id)


detect = on(
    type="message_sent",
    rule=_rule,
    block=False,
    priority=0,
)


@detect.handle()
async def _(bot: Bot, event: Event):
    if repeat_check_on and group_self_message.check_group_repeat(
        group_id=event.group_id, message=event.message
    ):
        permission_manager.set_group_perm(
            group_id=event.group_id, permission=BLACK, duration=repeat_ban_time
        )
        await detect.send(
            f"检测到{list(bot.config.nickname)[0]}在{repeat_check_duration}s内连续发送了{repeat_limit}条相同消息，为防止刷屏，静默{repeat_ban_time}s"
        )
    elif send_on and group_self_message.check_group_send(group_id=event.group_id):
        permission_manager.set_group_perm(
            group_id=event.group_id, permission=BLACK, duration=send_ban_time
        )
        await detect.send(
            f"检测到{list(bot.config.nickname)[0]}在{send_duration}s内发送了{send_limit}条消息，为防止刷屏，静默{send_ban_time}s"
        )
