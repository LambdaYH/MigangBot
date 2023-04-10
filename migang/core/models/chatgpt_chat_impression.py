from tortoise import fields
from tortoise.models import Model


class ChatGPTChatImpression(Model):
    user_id = fields.BigIntField(null=False)
    group_id = fields.BigIntField(null=True)
    self_id = fields.BigIntField(null=False)
    impression = fields.TextField()
    time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "chatgpt_chat_impression"
        table_description = "chatgpt的bot对用户的印象记录"
