import asyncio
from random import random, shuffle
from typing import Dict, List, Union, Iterable, Optional

from nonebot import get_bot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    ActionFailed,
    NetworkError,
    MessageSegment,
)

from migang.core.manager import group_manager, group_bot_manager


class SendManager:
    def __init__(
        self,
        bot: Bot,
        group_list: List[int],
        msg: Iterable[Union[Message, MessageSegment]],
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
                    except (ActionFailed, NetworkError) as e:
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
                        except (ActionFailed, NetworkError) as e:
                            logger.error(f"GROUP {group} 消息发送失败 {type(e)}: {e}")
                    if not self.failed_dict[group]:
                        self.failed_dict.pop(group)

            if not self.failed_dict:
                break
            logger.warning(
                f"剩余 {len(self.failed_dict)} 个消息发送失败，重试次数{i+1}/{self.retry_limit}"
            )
            await asyncio.sleep(self.retry_interval)

    async def do(self):
        if self.forward:
            for group in self.group_list:
                await asyncio.sleep(random() + 0.3)
                try:
                    await self.bot.send_group_forward_msg(
                        group_id=group, messages=self.msg
                    )
                except (ActionFailed, NetworkError) as e:
                    logger.error(f"GROUP {group} 消息发送失败 {type(e)}: {e}")
                    # blocked by server时不处理
                    if isinstance(
                        e, ActionFailed
                    ) and "blocked by server" in e.info.get("message", ""):
                        pass
                    else:
                        self.failed_dict[group] = True
        else:
            for group in self.group_list:
                for i, m in enumerate(self.msg):
                    await asyncio.sleep(random() + 0.3)
                    try:
                        await self.bot.send_group_msg(group_id=group, message=m)
                    except (ActionFailed, NetworkError) as e:
                        logger.error(f"GROUP {group} 消息发送失败 {type(e)}: {e}")
                        if isinstance(
                            e, ActionFailed
                        ) and "blocked by server" in e.info.get("message", ""):
                            pass
                        else:
                            if group not in self.failed_dict:
                                self.failed_dict[group] = set()
                            self.failed_dict[group].add(i)
        if self.failed_dict:
            logger.warning(f"共 {len(self.failed_dict)} 个消息发送失败，即将重试")
            await asyncio.sleep(self.retry_interval)
            await self.retry()


async def broadcast(
    task_name: str,
    msg: Union[Iterable[Union[Message, MessageSegment]], Message, MessageSegment, str],
    forward: bool = False,
) -> None:
    """将消息推送到task_name启用的所有群

    Args:
        task_name (str): 任务名
        msg (Union[Iterable[Union[Message, MessageSegment]], Message, MessageSegment]): 消息
        forward (bool, optional): 若以转发模式，则True. Defaults to False.
        bot (Optional[Bot], optional): 选定的bot. Defaults to None.
    """
    group_bot_list = group_bot_manager.get_valid_group()
    bot_group_map: Dict[Bot, List[int]] = {}
    for bot, group_id in group_bot_list:
        if bot not in bot_group_map:
            bot_group_map[bot] = []
        if group_manager.check_group_task_status(
            task_name=task_name, group_id=group_id
        ):
            bot_group_map[bot].append(group_id)
    for group_list in bot_group_map.values():
        shuffle(group_list)
    if isinstance(msg, str):
        msg = Message(msg)
    if isinstance(msg, Message) or isinstance(msg, MessageSegment):
        msg = (msg,)
    for bot, group_list in bot_group_map.items():
        await SendManager(bot=bot, group_list=group_list, msg=msg, forward=forward).do()
