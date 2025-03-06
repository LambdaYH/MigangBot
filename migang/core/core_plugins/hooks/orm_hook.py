"""
本文件主要用于hook Orm
"""

from nonebot import require
from sqlalchemy import event
from tortoise.signals import pre_save

require("nonebot_plugin_chatrecorder")

from nonebot_plugin_chatrecorder.model import MessageRecord

from migang.core.models import ChatGPTChatHistory


def clean_fields(mapper, connection, target):
    if isinstance(target.message, dict) or isinstance(target.message, list):
        target.message = clean_json_message(target.message)

    if target.plain_text:
        target.plain_text = target.plain_text.replace("\u0000", "")


def clean_json_message(message):
    if isinstance(message, dict):
        return {k: clean_json_message(v) for k, v in message.items()}
    elif isinstance(message, list):
        return [clean_json_message(item) for item in message]
    elif isinstance(message, str):
        return message.replace("\u0000", "")
    else:
        return message


# 注册监听器
event.listen(MessageRecord, "before_insert", clean_fields)
event.listen(MessageRecord, "before_update", clean_fields)


@pre_save(ChatGPTChatHistory)
async def _(
    sender: type[ChatGPTChatHistory],
    instance: ChatGPTChatHistory,
    using_db,
    update_fields,
) -> None:
    instance.message = clean_json_message(instance.message)
