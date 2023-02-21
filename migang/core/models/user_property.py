from typing import Optional

from tortoise import fields
from tortoise.functions import Max
from tortoise.models import Model


class UserProperty(Model):
    user_id = fields.BigIntField(pk=True)
    gold = fields.BigIntField(null=False, default=0)
    impression = fields.DecimalField(12, 3, default=0)

    class Meta:
        table = "user_property"
        table_description = "与用户相关的各项可变动属性记录"
