from tortoise import fields
from tortoise.models import Model

from aerich_config_helper.model.permission import Permission


class GroupStatus(Model):
    group_id = fields.BigIntField(unique=True)
    permission = fields.IntEnumField(enum_type=Permission)
    bot_status = fields.BooleanField(default=True)

    class Meta:
        table = "group_status"
        table_description = "管理群相关状态"
