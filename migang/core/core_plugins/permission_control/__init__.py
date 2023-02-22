import re
from datetime import timedelta
from typing import Tuple, Union

from nonebot import on_regex
from nonebot.params import RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from migang.core.permission import Permission
from migang.core.manager import permission_manager

__plugin_meta__ = PluginMetadata(
    name="权限控制",
    description="控制用户以及群权限",
    usage="""
usage：
    指令：
        设置用户权限 用户 等级 时长（可选）
        设置群权限 群 等级 时长（可选）
""".strip(),
    extra={
        "unique_name": "migang_permission_control",
        "example": "设置用户/群权限",
        "author": "migang",
        "version": 0.1,
    },
)

perm_ctl = on_regex(
    r"^设[置定](用户|群)权限 ?(\d+) (\d) ?([\s\S\d]+)?",
    priority=1,
    permission=SUPERUSER,
    block=True,
)

INT_TO_PERM = {
    1: Permission.BLACK,
    2: Permission.BAD,
    3: Permission.NORMAL,
    4: Permission.GOOD,
    5: Permission.EXCELLENT,
}


@perm_ctl.handle()
async def _(reg_groups: Tuple = RegexGroup()):
    if len(reg_groups) < 3:
        await perm_ctl.finish("指令错误，请按照 设置用户/群权限 用户 等级 （时长） 重新输入")
    type_ = reg_groups[0]
    target_id = int(reg_groups[1])
    perm_int = int(reg_groups[2])
    if perm_int < 1:
        perm = Permission.BLACK
    elif perm_int > 5:
        perm = Permission.EXCELLENT
    else:
        perm = INT_TO_PERM[perm_int]
    duration: Union[timedelta, int, None] = None
    if reg_groups[3]:
        if reg_groups[3].isdigit():
            duration = timedelta(seconds=int(reg_groups[3]))
        else:
            seconds, minutes, hours, days = 0, 0, 0, 0
            if result := re.search(r"s:(\d+)", reg_groups[3]):
                seconds = int(result.group(1))
            if result := re.search(r"m:(\d+)", reg_groups[3]):
                minutes = int(result.group(1))
            if result := re.search(r"h:(\d+)", reg_groups[3]):
                hours = int(result.group(1))
            if result := re.search(r"d:(\d+)", reg_groups[3]):
                days = int(result.group(1))
            duration = timedelta(
                days=days, minutes=minutes, hours=hours, seconds=seconds
            )
    if type_ == "用户":
        permission_manager.set_user_perm(
            user_id=target_id, permission=perm, duration=duration
        )
    else:
        permission_manager.set_group_perm(
            group_id=target_id, permission=perm, duration=duration
        )
    await perm_ctl.send(
        f"已设定{type_}的权限为 {perm}" + (f"持续时长为 {duration}" if duration else "")
    )
