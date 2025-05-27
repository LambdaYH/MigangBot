from tortoise import fields
from tortoise.models import Model


class UserStatus(Model):
    user_id = fields.BigIntField(null=False)
    status = fields.CharField(max_length=32, null=False)

    class Meta:
        table = "user_status"
        table_description = "用户状态信息"
