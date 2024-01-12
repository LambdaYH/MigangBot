from tortoise import fields
from tortoise.models import Model

from migang.core.permission import Permission
from migang.core.constant import ID_MAX_LENGTH


class UserStatus(Model):
    user_id = fields.CharField(max_length=ID_MAX_LENGTH, unique=True)
    permission = fields.IntEnumField(enum_type=Permission)

    class Meta:
        table = "user_status"
        table_description = "管理用户相关状态"
