from tortoise import fields
from tortoise.models import Model

from migang.core.permission import Permission
from migang.core.constant import ID_MAX_LENGTH


class GroupStatus(Model):
    group_id = fields.CharField(max_length=ID_MAX_LENGTH, unique=True)
    permission = fields.IntEnumField(enum_type=Permission)
    bot_status = fields.BooleanField(default=True)

    class Meta:
        table = "group_status"
        table_description = "管理群相关状态"
