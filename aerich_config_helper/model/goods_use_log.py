from tortoise import fields
from tortoise.models import Model


class GoodsUseLog(Model):
    user_id = fields.BigIntField(null=False)
    goods_id = fields.IntField(null=False)
    count = fields.IntField(default=1)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "goods_use_log"
        table_description = "物品使用记录"
