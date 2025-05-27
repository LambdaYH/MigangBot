from tortoise import fields
from tortoise.models import Model


class UserProperty(Model):
    user_id = fields.BigIntField(null=False)
    property_name = fields.CharField(max_length=64, null=False)
    property_value = fields.CharField(max_length=255, null=True)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_property"
        table_description = "用户属性信息"
