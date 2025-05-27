from tortoise import fields
from tortoise.models import Model


class UserBag(Model):
    user_id = fields.BigIntField(null=False)
    goods_id = fields.IntField(null=False)
    count = fields.IntField(default=0)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_bag"
        table_description = "用户背包信息"
