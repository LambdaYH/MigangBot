from typing import Optional

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Max


class ChatGPTChatHistory(Model):
    user_id = fields.BigIntField(null=False)
    group_id = fields.BigIntField(null=True)
    target_id = fields.BigIntField(null=True, default=None)
    """仅bot回复时记录"""
    triggered = fields.BooleanField(default=False)
    """是普通对话还是触发了的对话"""
    message = fields.JSONField()
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chatgpt_chat_history"
        table_description = "chatgpt的历史会话记录"
