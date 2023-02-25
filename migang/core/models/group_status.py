from tortoise import fields
from tortoise.models import Model

from migang.core.permission import Permission


class GroupStatus(Model):
    group_id = fields.BigIntField(unique=True)
    permission = fields.IntEnumField(enum_type=Permission)
    bot_status = fields.BooleanField(default=True)

    class Meta:
        table = "group_status"
        table_description = "管理群相关状态"

    def __hash__(self) -> int:
        return hash(self.group_id)

    def set_bot_enable(self) -> bool:
        """启用群机器人

        Returns:
            bool: 若True，则启用成功，反之则表示处于启用状态
        """
        if self.bot_status:
            return False
        self.bot_status = True
        return True

    def set_bot_disable(self) -> bool:
        """禁用群机器人

        Returns:
            bool: 若True，则禁用成功，反之则表示处于禁用状态
        """
        if not self.bot_status:
            return False
        self.bot_status = False
        return True

    def set_permission(self, permission: Permission):
        """设定群权限

        Args:
            permission (Permission): 新权限
        """
        self.permission = permission
