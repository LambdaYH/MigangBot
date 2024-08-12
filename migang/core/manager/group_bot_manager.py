import random
import asyncio
from typing import Dict, List, Tuple

from nonebot.log import logger
from nonebot import get_bot, get_bots
from nonebot.adapters.onebot.v11 import Bot, ActionFailed


class GroupBotManager:
    """管理群消息使用哪个机器人处理"""

    def __init__(self) -> None:
        self.__group_bot: Dict[int, List[int]] = {}

    def del_bot(self, bot_id: int):
        for bots in self.__group_bot.values():
            if bot_id in bots:
                bots.remove(bot_id)
        logger.info(f"已卸载bot：{bot_id}")

    async def add_bot(self, bot: Bot) -> bool:
        """添加群机器人"""
        return await self.__add_bot(bot, self.__group_bot)

    async def __add_bot(self, bot: Bot, group_bot: Dict[int, List[int]]) -> bool:
        """添加群机器人"""
        self_id = int(bot.self_id)
        try:
            group_list = await bot.get_group_list()
            group_list = [int(group["group_id"]) for group in group_list]
            for group in group_list:
                if group not in group_bot:
                    group_bot[group] = []
                group_bot[group].append(self_id)
            logger.info(f"已装载bot：{self_id}")
            return True
        except ActionFailed:
            logger.error(f"获取bot：{self_id}的群列表失败")
            return False

    async def handle_group_kick(self, bot_id: int, group_id: int):
        group_bots = self.__group_bot.get(group_id)
        if not group_bots or bot_id not in group_bots:
            return
        group_bots.remove(bot_id)

    async def handle_group_add(self, bot_id: int, group_id: int):
        if group_id not in self.__group_bot:
            self.__group_bot[group_id] = []
        self.__group_bot[group_id].append(bot_id)

    async def refreshAll(self):
        logger.info("开始刷新群")
        bots = get_bots().values()
        group_bot_temp = {}
        for bot in bots:
            if not await self.__add_bot(bot, group_bot_temp):
                return
            await asyncio.sleep(12.06)
        self.__group_bot = group_bot_temp
        logger.info("群刷新结束")

    def check_group_bot(self, group_id: int, bot_id: int) -> bool:
        """检查群机器人，取list中的第一个

        Returns:
            bool: 检查通过返回True
        """
        group_bots = self.__group_bot.get(group_id)
        if not group_bots:
            return True
        return group_bots[0] == bot_id

    def shuffle_group_bot(self):
        """更换群机器人的顺序"""
        for group_bots in self.__group_bot.values():
            random.shuffle(group_bots)

    def get_valid_group(self) -> List[Tuple[Bot, int]]:
        """获取每个群的群机器人，返回 bot，群号"""
        group_list = []
        bot_dict: Dict[int, Bot] = {}
        for k, v in self.__group_bot.items():
            if v:
                bot_id = random.choice(v)  # 随机获取本群可用bot
                if bot_id not in bot_dict:
                    bot_dict[bot_id] = get_bot(str(bot_id))
                group_list.append((bot_dict[bot_id], k))
        return group_list

    def get_bot(self, group_id: str | int) -> Bot:
        if isinstance(group_id, str):
            group_id = int(group_id)
        if group_bots := self.__group_bot.get(group_id):
            return get_bot(str(group_bots[0]))
        raise Exception(f"该群{group_id}不存在群机器人！！")
