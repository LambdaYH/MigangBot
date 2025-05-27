from tortoise import fields
from tortoise.models import Model


class GoodsGroup(Model):
    group_id = fields.BigIntField(null=False)
    goods_id = fields.IntField(null=False)
    count = fields.IntField(default=0)

    class Meta:
        table = "goods_group"
        table_description = "群物品信息"
