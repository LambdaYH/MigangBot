from tortoise import fields
from tortoise.models import Model


class Feedback(Model):
    user_id = fields.BigIntField(null=False)
    content = fields.TextField(null=False)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "feedback"
        table_description = "用户反馈记录"
