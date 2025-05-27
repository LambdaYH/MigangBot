from tortoise import fields
from tortoise.models import Model


class GroupWelcome(Model):
    group_id = fields.BigIntField(null=False)
    welcome_message = fields.TextField(null=True)

    class Meta:
        table = "group_welcome"
        table_description = "群欢迎语信息"
