from tortoise import fields
from tortoise.models import Model

from migang.core.constant import ID_MAX_LENGTH


class GroupWelcome(Model):
    group_id = fields.CharField(max_length=ID_MAX_LENGTH)
    content = fields.JSONField(null=True)
    status = fields.BooleanField(default=True)

    class Meta:
        table = "group_welcome"
        table_description = "群欢迎语"
