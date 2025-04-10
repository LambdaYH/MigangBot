from nonebot import get_bot, on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent

from migang.core import TaskItem, broadcast

from .data_source import get_epic_free

__plugin_meta__ = PluginMetadata(
    name="epic免费游戏",
    description="可以不玩，不能没有，每日白嫖",
    usage="""
usage：
    可以不玩，不能没有，每日白嫖
    指令：
        epic喜加一
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_task__ = TaskItem(task_name="epic_free_game", name="epic免费游戏推送")


epic = on_fullmatch("epic喜加一", priority=5, block=True)


@epic.handle()
async def handle(bot: Bot, event: MessageEvent):
    msg_list, code = await get_epic_free(event.self_id)
    if code == 404:
        await epic.finish(msg_list)
    if isinstance(event, GroupMessageEvent):
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
    msg_list, code = await get_epic_free(int(bot.self_id))
    await broadcast(task_name="epic_free_game", msg=msg_list, forward=code == 200)
