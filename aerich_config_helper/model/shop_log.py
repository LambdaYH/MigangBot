from tortoise import fields
from tortoise.models import Model


class ShopLog(Model):
    user_id = fields.BigIntField(null=False)
    goods_id = fields.IntField(null=False)
    count = fields.IntField(default=1)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "shop_log"
        table_description = "用户商店购买记录"
