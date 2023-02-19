from nonebot import on_message
from nonebot.adapters.onebot.v11 import GROUP, Bot, GroupMessageEvent, Message
from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me

from migang.core import ConfigItem, get_config

from .data_source import get_chat_result, hello, no_result

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
    ConfigItem(key="turing_key", description="图灵机器人 key https://www.turingapi.com/"),
    ConfigItem(
        key="text_filter",
        initial_value=["鸡", "口交"],
        default_value=[],
        description="回答过滤词，会以*呈现",
    ),
)


ai = on_message(rule=to_me(), priority=998, permission=GROUP)

hello_msg = set(
    [
        "你好啊",
        "你好",
        "在吗",
        "在不在",
        "您好",
        "您好啊",
        "你好",
        "在",
    ]
)


@ai.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    if "CQ:xml" in str(event.message):
        return
    # 打招呼
    msg = event.get_plaintext()
    img = [seg.data["url"] for seg in event.message]
    if msg or msg in hello_msg:
        await ai.finish(hello())
    img = img[0] if img else ""
    nickname = event.sender.card or event.sender.nickname
    result = await get_chat_result(msg, img, event.user_id, nickname)
    logger.info(
        f"用户 {event.user_id} 群 {event.group_id if isinstance(event, GroupMessageEvent) else ''} "
        f"问题：{msg} ---- 回答：{result}"
    )
    if result:
        result = str(result)
        for t in await get_config("text_filter"):
            result = result.replace(t, "*")
        await ai.finish(Message(result))
    else:
        await ai.finish(no_result())
