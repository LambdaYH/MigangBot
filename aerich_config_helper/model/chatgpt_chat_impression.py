from tortoise import fields
from tortoise.models import Model


class ChatGPTChatImpression(Model):
    user_id = fields.BigIntField(null=False)
    impression = fields.CharField(max_length=255, null=False)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chatgpt_chat_impression"
        table_description = "chatgpt的印象记录"
