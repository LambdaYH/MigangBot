from tortoise import fields
from tortoise.models import Model


class GroupWelcome(Model):
    group_id = fields.BigIntField()
    content = fields.JSONField(null=True)
    status = fields.BooleanField(default=True)

    class Meta:
        table = "group_welcome"
        table_description = "群欢迎语"
