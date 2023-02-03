from nonebot.log import logger
from nonebot import on_fullmatch
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, GroupMessageEvent

from migangbot.core.manager import group_manager

switch_bot_wakeup = on_fullmatch(
    ("起床啦", "醒来吧", "醒来", "起床"),
    priority=1,
    block=True,
    permission=GROUP_ADMIN | GROUP_OWNER,
)

switch_bot_sleep = on_fullmatch(
    ("休息吧", "睡吧"),
    priority=1,
    block=True,
    permission=GROUP_ADMIN | GROUP_OWNER,
)


@switch_bot_wakeup.handle()
async def _(
    event: GroupMessageEvent,
):
    if group_manager.EnableBot(group_id=event.group_id):
        logger.info(f"群 {event.group_id} 唤醒了Bot")
        await switch_bot_wakeup.finish("呜..醒来了...")
    await switch_bot_wakeup.send("我一直醒着呢！")


@switch_bot_sleep.handle()
async def _(event: GroupMessageEvent):
    if group_manager.DisableBot(group_id=event.group_id):
        logger.info(f"群 {event.group_id} 的Bot下班了")
        await switch_bot_sleep.finish("那我去睡觉了哦~")
    await switch_bot_sleep.send("zzzzzz......")
