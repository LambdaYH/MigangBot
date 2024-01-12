from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters import Bot, Event
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException

from migang.core.models import UserProperty
from migang.core.cross_platform import Session
from migang.core.manager import cd_manager, user_manager, count_manager, group_manager

_ignore_plugins = set(["switch_bot"])


@run_preprocessor
async def _(bot: Bot, matcher: Matcher, event: Event, state: T_State, session: Session):
    if matcher.plugin_name in _ignore_plugins:
        return

    # 检测群权限
    if session.is_group:
        if not group_manager.check_group_plugin_status(
            plugin_name=matcher.plugin_name, group_id=session.group_id
        ):
            raise IgnoredException("群插件不可用")

    # 如果是自己的消息就不检测了
    if session.user_id == bot.self_id:
        return

    # 后续所有动作都建立在有用户的基础上
    if session.has_user:
        # 检测个人权限
        if not user_manager.check_user_plugin_status(
            plugin_name=matcher.plugin_name, user_id=session.user_id
        ):
            raise IgnoredException("个人权限不足")

        # 检测插件CD
        if (
            ret := cd_manager.check(plugin_name=matcher.plugin_name, session=session)
        ) != True:
            if ret != None:
                await matcher.send(ret)
            raise IgnoredException("cd...")

        # 检查插件次数限制
        if (
            ret := count_manager.check(plugin_name=matcher.plugin_name, session=session)
        ) != True:
            if ret != None:
                await matcher.send(ret)
            raise IgnoredException("count...")

        state["__migang_session__"] = session

        # 检查通过后把事件的sender昵称替换为昵称系统昵称

        # Onebot11
        if bot.adapter.get_name == "OneBot V11":
            if (
                hasattr(event, "sender")
                and (
                    name := await UserProperty.filter(user_id=session.user_id)
                    .first()
                    .values_list("nickname")
                )
                and (name[0] is not None)
            ):
                event.sender.nickname = name[0]
