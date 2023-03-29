from nonebot import on_fullmatch, get_bot
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageEvent
from nonebot_plugin_apscheduler import scheduler

from migang.core import TaskItem, broadcast

from .data_source import get_epic_free

__zx_plugin_name__ = "epic免费游戏"
__plugin_usage__ = """
usage：
    可以不玩，不能没有，每日白嫖
    指令：
        epic喜加一
""".strip()
__plugin_des__ = "可以不玩，不能没有，每日白嫖"
__plugin_cmd__ = ["epic"]
__plugin_version__ = 0.1
__plugin_author__ = "AkashiCoin"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["epic"],
}
__plugin_task__ = TaskItem(task_name="epic_free_game", name="epic免费游戏")


epic = on_fullmatch("epic喜加一", priority=5, block=True)


@epic.handle()
async def handle(bot: Bot, event: MessageEvent):
    Type_Event = "Private"
    if isinstance(event, GroupMessageEvent):
        Type_Event = "Group"
    msg_list, code = await get_epic_free(bot, Type_Event)
    if code == 404:
        await epic.send(msg_list)
    elif isinstance(event, GroupMessageEvent):
        await bot.send_forward_msg(group_id=event.group_id, messages=msg_list)
    else:
        await bot.send_forward_msg(user_id=event.user_id, message=msg_list)


# epic免费游戏
@scheduler.scheduled_job(
    "cron",
    hour=12,
    minute=1,
)
async def _():
    bot = get_bot()
    msg_list, code = await get_epic_free(bot, "Group")
    await broadcast(
        task_name="epic_free_game", msg=msg_list, forward=code == 200, bot=bot
    )
