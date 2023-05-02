from tortoise import fields
from tortoise.models import Model

from migang.core.permission import Permission


class UserStatus(Model):
    user_id = fields.BigIntField(unique=True)
    permission = fields.IntEnumField(enum_type=Permission)

    class Meta:
        table = "user_status"
        table_description = "管理用户相关状态"
