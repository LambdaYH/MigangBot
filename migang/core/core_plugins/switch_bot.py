"""关闭或启用Bot
"""

from nonebot.log import logger
from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, GroupMessageEvent

from migang.core.manager import group_manager

switch_bot_wakeup = on_fullmatch(
    ("起床啦", "醒来吧", "醒来", "起床"),
    priority=1,
    rule=to_me(),
    block=True,
    permission=GROUP_ADMIN | GROUP_OWNER,
)

switch_bot_sleep = on_fullmatch(
    ("休息吧", "睡吧"),
    priority=1,
    rule=to_me(),
    block=True,
    permission=GROUP_ADMIN | GROUP_OWNER,
)


@switch_bot_wakeup.handle()
async def _(
    event: GroupMessageEvent,
):
    if group_manager.enable_bot(group_id=event.group_id):
        logger.info(f"群 {event.group_id} 唤醒了Bot")
        await switch_bot_wakeup.finish("呜..醒来了...")
    await switch_bot_wakeup.send("我一直醒着呢！")


@switch_bot_sleep.handle()
async def _(event: GroupMessageEvent):
    if group_manager.disable_bot(group_id=event.group_id):
        logger.info(f"群 {event.group_id} 的Bot下班了")
        await switch_bot_sleep.finish("那我去睡觉了哦~")
    await switch_bot_sleep.send("zzzzzz......")
