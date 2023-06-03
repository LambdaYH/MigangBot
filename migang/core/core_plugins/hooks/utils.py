from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Event
from nonebot.exception import IgnoredException

from migang.core.models import UserProperty
from migang.core.manager import cd_manager, count_manager


async def check_event(matcher: Matcher, event: Event) -> None:
    # 检测插件CD
    if (ret := cd_manager.check(plugin_name=matcher.plugin_name, event=event)) != True:
        if ret != None:
            await matcher.send(ret)
        raise IgnoredException("cd...")
    # 检查插件次数限制
    if (
        ret := count_manager.check(plugin_name=matcher.plugin_name, event=event)
    ) != True:
        if ret != None:
            await matcher.send(ret)
        raise IgnoredException("count...")
    # 检查通过后把事件的sender昵称替换为昵称系统昵称
    if (
        hasattr(event, "sender")
        and (
            name := await UserProperty.filter(user_id=event.user_id)
            .first()
            .values_list("nickname")
        )
        and (name[0] is not None)
    ):
        event.sender.nickname = name[0]
