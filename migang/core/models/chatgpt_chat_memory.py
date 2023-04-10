from typing import Optional

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Max


class ChatGPTChatMemory(Model):
    group_id = fields.BigIntField(null=False)
    user_id = fields.BigIntField(null=False)
    self_id = fields.BigIntField(null=False)
    memory_key = fields.TextField()
    memory_value = fields.TextField()
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chatgpt_chat_memory"
        table_description = "chatgpt的记忆"
