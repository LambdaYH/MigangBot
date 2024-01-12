import random
from typing import List
from pathlib import Path

from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.adapters import Bot, Event
from nonebot.plugin import PluginMetadata
from nonebot import on_keyword, on_message
from nonebot_plugin_alconna import Text, UniMsg, UniMessage
from nonebot_plugin_userinfo import UserInfo, EventUserInfo

from migang.core.cross_platform import GROUP
from migang.core import Session, ConfigItem, get_config
from migang.core.utils.image import image_file_to_bytes
from migang.core.cross_platform.adapters import supported_adapters

from .message_manager import MessageManager
from .chatgpt import do_chat, not_at_rule, get_gpt_chat
from .data_source import hello, no_result, anti_zuichou

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="chat_",
    description="与Bot进行对话",
    usage="""
usage：
    与Bot普普通通的对话吧！
""".strip(),
    type="application",
    supported_adapters=supported_adapters,
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
message_manager = MessageManager(hello, anti_zuichou, get_gpt_chat, no_result)
# 没at时候把消息送给naturel_gpt处理
on_message(
    priority=998, block=False, rule=not_at_rule, permission=GROUP
).append_handler(do_chat)


@chat.handle()
async def _(
    matcher: Matcher,
    bot: Bot,
    event: Event,
    message: UniMsg,
    session: Session,
    user_info: UserInfo = EventUserInfo(),
):
    plain_text = event.get_plaintext()
    if "CQ:xml" in str(message) or plain_text.startswith("/"):
        return
    reply = await message_manager.reply(
        session=session,
        user_name=user_info.user_name,
        nickname=list(bot.config.nickname)[0],
        bot=bot,
        matcher=matcher,
        plain_text=event.get_plaintext(),
        event=event,
        message=message,
    )
    if not reply:
        return
    logger.info(
        f"用户 {session.user_id} 群 {session.group_id if session.is_group else ''} "
        f"问题：{message} ---- 回答：{reply}"
    )
    texts: List[Text] = reply.get(Text)
    for text in texts:
        for t in await get_config("text_filter"):
            text.text = text.text.replace(t, "*")
    await reply.send()


# 加一点祖传回复


wenhao = on_keyword(("??", "？？"), priority=99, block=False, permission=GROUP)
tanhao = on_keyword(("!!", "！！"), priority=99, block=False, permission=GROUP)
huoguo = on_keyword(("火锅",), priority=99, block=False, permission=GROUP)

custom_chat_path = Path(__file__).parent / "image" / "custom_chat"


@wenhao.handle()
async def _():
    if random.random() < 0.30:
        await UniMessage.image(
            await image_file_to_bytes(custom_chat_path / "wenhao.jpg")
        ).send()


@tanhao.handle()
async def _():
    if random.random() < 0.30:
        await UniMessage.image(
            await image_file_to_bytes(custom_chat_path / "tanhao.jpg")
        ).send()


@huoguo.handle()
async def _():
    if random.random() < 0.30:
        await UniMessage.image(
            await image_file_to_bytes(custom_chat_path / "huoguo.jpg")
        ).send()
