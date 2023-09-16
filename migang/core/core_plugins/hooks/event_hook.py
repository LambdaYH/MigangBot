from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters import Bot, Event
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot_plugin_session import SessionLevel, SessionIdType, extract_session

from migang.core.models import PlatformId, UserProperty
from migang.core.manager import cd_manager, user_manager, count_manager, group_manager

_ignore_plugins = set(["switch_bot"])


@run_preprocessor
async def _(
    bot: Bot,
    matcher: Matcher,
    event: Event,
    state: T_State,
):
    print(111)
    if matcher.plugin_name in _ignore_plugins:
        return
    # 提取session
    session = extract_session(bot=bot, event=event)
    # 构建平台标识符
    platform = f"{session.bot_type}_{session.platform}"

    # 提取出用户id，如果level>level1则视为群聊
    user_id: str = session.get_id(
        SessionIdType.USER,
        include_platform=False,
        include_bot_type=False,
        include_bot_id=False,
    )
    group_id: str = (
        session.get_id(
            SessionIdType.GROUP,
            include_platform=False,
            include_bot_type=False,
            include_bot_id=False,
        )
        if session.level > SessionLevel.LEVEL1
        else None
    )

    # 提取出migang_id
    migang_user_id: int = await PlatformId.extract_migang_user_id(
        platform=platform, user_id=user_id
    )

    if group_id is not None:
        migang_group_id: int = await PlatformId.extract_migang_group_id(
            platform=platform, group_id=group_id
        )
        if not group_manager.check_group_plugin_status(
            plugin_name=matcher.plugin_name, group_id=migang_group_id
        ):
            raise IgnoredException("群插件不可用")
        state["migang_group_id"] = migang_group_id

    # 检测个人权限
    if not user_manager.check_user_plugin_status(
        plugin_name=matcher.plugin_name, user_id=migang_user_id
    ):
        raise IgnoredException("个人权限不足")
    state["migang_user_id"] = migang_user_id

    # 检测插件CD
    if (ret := cd_manager.check(plugin_name=matcher.plugin_name, state=state)) != True:
        if ret != None:
            await matcher.send(ret)
        raise IgnoredException("cd...")
    # 检查插件次数限制
    if (
        ret := count_manager.check(plugin_name=matcher.plugin_name, state=state)
    ) != True:
        if ret != None:
            await matcher.send(ret)
        raise IgnoredException("count...")

    # 检查通过后把事件的sender昵称替换为昵称系统昵称
    if (
        hasattr(event, "sender")
        and (
            name := await UserProperty.filter(user_id=migang_user_id)
            .first()
            .values_list("nickname")
        )
        and (name[0] is not None)
    ):
        event.sender.nickname = name[0]
