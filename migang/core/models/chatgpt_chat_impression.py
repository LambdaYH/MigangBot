from tortoise import fields
from tortoise.models import Model


class ChatGPTChatImpression(Model):
    """不同群独立印象（由于不同群的昵称不太一样，可能导致混乱，所以只能独立）"""

    user_id = fields.BigIntField(null=False)
    group_id = fields.BigIntField(null=False)
    self_id = fields.BigIntField(null=False)
    impression = fields.TextField()
    time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "chatgpt_chat_impression"
        table_description = "chatgpt的对用户的印象记录，各群独立"
        unique_together = ("user_id", "group_id", "self_id")
