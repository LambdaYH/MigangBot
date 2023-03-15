import random
from pathlib import Path

from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.plugin import PluginMetadata
from nonebot import on_keyword, on_message
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    Message,
    MessageSegment,
    GroupMessageEvent,
)

from migang.core import ConfigItem, get_config

from .message_manager import MessageManager
from .data_source import hello, no_result, get_turing, anti_zuichou

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="chat_",
    description="与Bot进行对话",
    usage="""
usage：
    与Bot普普通通的对话吧！
""".strip(),
    extra={
        "unique_name": "migang_chat",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_config__ = (
    ConfigItem(
        key="turing_keys",
        initial_value=["key1", "key2"],
        default_value=[],
        description="图灵机器人 key https://www.turingapi.com/",
    ),
    ConfigItem(
        key="text_filter",
        initial_value=["鸡", "口交"],
        default_value=[],
        description="回答过滤词，会以*呈现",
    ),
)


chat = on_message(rule=to_me(), priority=998, permission=GROUP)
message_manager = MessageManager(hello, anti_zuichou, get_turing, no_result)


@chat.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    if "CQ:xml" in str(event.message) or event.get_plaintext().startswith("/"):
        return
    user_name = event.sender.card or event.sender.nickname
    reply = await message_manager.reply(
        user_id=event.user_id,
        user_name=user_name,
        nickname=list(bot.config.nickname)[0],
        bot=bot,
        plain_text=event.get_plaintext(),
        event=event,
    )
    logger.info(
        f"用户 {event.user_id} 群 {event.group_id if isinstance(event, GroupMessageEvent) else ''} "
        f"问题：{event.message} ---- 回答：{reply}"
    )
    reply = str(reply)
    for t in await get_config("text_filter"):
        reply = reply.replace(t, "*")
    await chat.send(Message(reply))


# 加一点祖传回复


wenhao = on_keyword(("??", "？？"), priority=99, block=False, permission=GROUP)
tanhao = on_keyword(("!!", "！！"), priority=99, block=False, permission=GROUP)
huoguo = on_keyword(("火锅",), priority=99, block=False, permission=GROUP)

custom_chat_path = Path(__file__).parent / "image" / "custom_chat"


@wenhao.handle()
async def _():
    if random.random() < 0.30:
        await wenhao.send(MessageSegment.image(custom_chat_path / "wenhao.jpg"))


@tanhao.handle()
async def _():
    if random.random() < 0.30:
        await tanhao.send(MessageSegment.image(custom_chat_path / "tanhao.jpg"))


@huoguo.handle()
async def _():
    if random.random() < 0.30:
        await huoguo.send(MessageSegment.image(custom_chat_path / "huoguo.jpg"))
