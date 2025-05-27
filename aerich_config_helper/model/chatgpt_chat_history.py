from tortoise import fields
from tortoise.models import Model


class ChatGPTChatHistory(Model):
    user_id = fields.BigIntField(null=False)
    """对话发起者"""
    group_id = fields.BigIntField(null=True)
    target_id = fields.BigIntField(null=True, default=None)
    """对话对象"""
    message = fields.JSONField()
    time = fields.DatetimeField(auto_now_add=True)
    is_bot = fields.BooleanField(default=False, description="是否为机器人回复")

    class Meta:
        table = "chatgpt_chat_history"
        table_description = "chatgpt的历史会话记录"
