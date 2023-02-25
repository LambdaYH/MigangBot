from tortoise import fields
from tortoise.models import Model

from migang.core.permission import Permission


class UserStatus(Model):
    user_id = fields.BigIntField(unique=True)
    permission = fields.IntEnumField(enum_type=Permission)
    bot_status = fields.BooleanField(default=True)

    class Meta:
        table = "user_status"
        table_description = "管理用户相关状态"

    def __hash__(self) -> int:
        return hash(self.user_id)

    def set_permission(self, permission: Permission):
        """设定用户权限

        Args:
            permission (Permission): 新权限
        """
        self.permission = permission
