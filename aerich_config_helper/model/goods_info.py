from tortoise import fields
from tortoise.models import Model


class GoodsInfo(Model):
    goods_id = fields.IntField(pk=True)
    name = fields.CharField(max_length=64)
    description = fields.TextField(null=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    type = fields.CharField(max_length=32)
    extra = fields.JSONField(null=True)

    class Meta:
        table = "goods_info"
        table_description = "物品信息表"
