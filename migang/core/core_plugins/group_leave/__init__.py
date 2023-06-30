from nonebot import on_notice
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, ActionFailed, GroupDecreaseNoticeEvent

from migang.core.manager import TaskItem
from migang.core.utils.task_operation import check_task

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="退群提醒_",
    description="群员退出时提醒",
    usage="",
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "群功能"

__plugin_task__ = TaskItem(task_name="group_leave", name="退群提醒", default_status=False)


def _rule(event: GroupDecreaseNoticeEvent) -> bool:
    return event.user_id != event.self_id and check_task(
        group_id=event.group_id, task_name="group_leave"
    )


group_decrease = on_notice(priority=1, block=False, rule=_rule)


@group_decrease.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    try:
        user_info = await bot.get_stranger_info(user_id=event.user_id)
        user_name = user_info["nickname"]
    except ActionFailed:
        user_name = "未知"
    if event.sub_type == "leave":
        rst = f"{user_name}({event.user_id})前往了星之海..."
    if event.sub_type == "kick":
        operator = await bot.get_group_member_info(
            user_id=event.operator_id, group_id=event.group_id
        )
        operator_name = operator["card"] if operator["card"] else operator["nickname"]
        rst = f"{user_name}({event.user_id}) 被 {operator_name} 送往了星之海."
    try:
        await group_decrease.send(rst)
    except ActionFailed:
        return
