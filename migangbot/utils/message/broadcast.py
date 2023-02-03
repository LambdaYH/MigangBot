import asyncio
from random import random
from typing import Union, Dict, List, Optional

from nonebot import get_bot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, Message, ActionFailed

from migangbot.core.manager import group_manager


class SendManager:
    def __init__(
        self,
        bot: Bot,
        group_list,
        msg: Union[List[Message], Message],
        forward=False,
        retry_limit: int = 3,
        retry_interval: int = 5,
    ):
        self.bot = bot
        self.group_list = group_list
        self.msg = msg
        self.forward = forward
        self.retry_limit = retry_limit
        self.retry_interval = retry_interval
        self.failed_dict: Dict[int, Union[set[int], bool]] = {}

    async def retry(self):
        for i in range(self.retry_limit):
            if self.forward:
                for group in list(self.failed_dict):
                    await asyncio.sleep(random() + 0.3)
                    try:
                        await self.bot.send_group_forward_msg(
                            group_id=group, messages=self.msg
                        )
                        self.failed_dict.pop(group)
                    except ActionFailed as e:
                        logger.error(f"GROUP {group} 消息发送失败 {type(e)}: {e}")
            else:
                for group in list(self.failed_dict):
                    for idx in list(self.failed_dict[group]):
                        await asyncio.sleep(random() + 0.3)
                        try:
                            await self.bot.send_group_msg(
                                group_id=group, message=self.msg[idx]
                            )
                            self.failed_dict[group].remove(idx)
                        except ActionFailed as e:
                            logger.error(f"GROUP {group} 消息发送失败 {type(e)}: {e}")
                    if not self.failed_dict[group]:
                        self.failed_dict.pop(group)

            if not self.failed_dict:
                break
            logger.warning(
                f"剩余 {len(self.failed_dict)} 个消息发送失败，重试次数{i+1}/{self.retry_limit}"
            )
            await asyncio.sleep(self.retry_interval)

    async def Do(self):
        if self.forward:
            for group in self.group_list:
                await asyncio.sleep(random() + 0.3)
                try:
                    await self.bot.send_group_forward_msg(
                        group_id=group, messages=self.msg
                    )
                except ActionFailed as e:
                    logger.error(f"GROUP {group} 消息发送失败 {type(e)}: {e}")
                    self.failed_dict[group] = True
        else:
            for group in self.group_list:
                for i, weibo in enumerate(self.msg):
                    await asyncio.sleep(random() + 0.3)
                    try:
                        await self.bot.send_group_msg(group_id=group, message=weibo)
                    except ActionFailed as e:
                        logger.error(f"GROUP {group} 消息发送失败 {type(e)}: {e}")
                        if group not in self.failed_dict:
                            self.failed_dict[group] = set()
                        self.failed_dict[group].add(i)
        if self.failed_dict:
            logger.warning(f"共 {len(self.failed_dict)} 个消息发送失败，即将重试")
            await asyncio.sleep(self.retry_interval)
            await self.retry()


async def Broadcast(
    task_name: str,
    msg: Union[List[Message], Message],
    forward: bool = False,
    bot: Optional[Bot] = None,
):
    if not bot:
        bot = get_bot()
    group_list = await bot.get_group_list()
    group_list = [
        group
        for group in group_list
        if group_manager.CheckGroupTaskStatus(task_name=task_name, group_id=group)
    ]
    await SendManager(bot=bot, group_list=group_list, msg=msg, forward=forward).Do()
