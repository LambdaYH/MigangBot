import random
from pathlib import Path

from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot import on_keyword, on_message
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    Message,
    MessageSegment,
    GroupMessageEvent,
)

from migang.core import pre_init_manager
from migang.core.utils.image import pic_file_to_bytes

from .exception import BreakSession
from .config import get_agent_config
from .agent import do_chat, pre_check
from .tools import *  # noqa: F401,F403
from .message_manager import MessageManager
from .settings import register_chat_agent_configs
from .data_source import hello, no_result, anti_zuichou

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="chat_agent",
    description="使用 Agent 完成对话和插件调用",
    usage="""
usage：
    @Bot 正常聊天即可，插件能力由 Agent 自主识别与调用。
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)


@pre_init_manager
async def _():
    await register_chat_agent_configs()


async def get_agent_chat(matcher: Matcher, event: GroupMessageEvent, bot: Bot):
    state = {}
    if await pre_check(event=event, bot=bot, state=state):
        await do_chat(matcher=matcher, event=event, bot=bot, state=state)
    raise BreakSession("chat_agent 已处理发送逻辑")


async def not_at_rule(bot: Bot, event: GroupMessageEvent, state) -> bool:
    if event.is_tome():
        return False
    return await pre_check(event=event, bot=bot, state=state)


chat_agent = on_message(rule=to_me(), priority=998, permission=GROUP)
message_manager = MessageManager(hello, anti_zuichou, get_agent_chat, no_result)
on_message(priority=998, block=False, rule=not_at_rule).append_handler(do_chat)


@chat_agent.handle()
async def _(matcher: Matcher, bot: Bot, event: GroupMessageEvent):
    if getattr(event, "llm_trigger", False):
        return
    if "CQ:xml" in str(event.message) or event.get_plaintext().startswith("/"):
        return
    user_name = event.sender.card or event.sender.nickname
    reply = await message_manager.reply(
        user_id=event.user_id,
        user_name=user_name,
        nickname=list(bot.config.nickname)[0],
        bot=bot,
        matcher=matcher,
        plain_text=event.get_plaintext(),
        event=event,
    )
    if not reply:
        return
    logger.info(
        f"用户 {event.user_id} 群 {event.group_id} 问题：{event.message} ---- 回答：{reply}"
    )
    reply_text = str(reply)
    for text in await get_agent_config("text_filter", default_value=[]):
        reply_text = reply_text.replace(text, "*")
    await chat_agent.send(Message(reply_text))


wenhao = on_keyword(("??", "？？"), priority=99, block=False, permission=GROUP)
tanhao = on_keyword(("!!", "！！"), priority=99, block=False, permission=GROUP)
huoguo = on_keyword(("火锅",), priority=99, block=False, permission=GROUP)

custom_chat_path = Path(__file__).parent.parent / "chat" / "image" / "custom_chat"


@wenhao.handle()
async def _():
    if random.random() < 0.30:
        await wenhao.send(
            MessageSegment.image(
                await pic_file_to_bytes(custom_chat_path / "wenhao.jpg")
            )
        )


@tanhao.handle()
async def _():
    if random.random() < 0.30:
        await tanhao.send(
            MessageSegment.image(
                await pic_file_to_bytes(custom_chat_path / "tanhao.jpg")
            )
        )


@huoguo.handle()
async def _():
    if random.random() < 0.30:
        await huoguo.send(
            MessageSegment.image(
                await pic_file_to_bytes(custom_chat_path / "huoguo.jpg")
            )
        )
