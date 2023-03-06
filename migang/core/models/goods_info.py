from tortoise import fields
from tortoise.models import Model


class GoodsInfo(Model):
    name = fields.CharField(255, unique=True)
    """商品名称"""
    price = fields.IntField()
    """价格"""
    description = fields.TextField()
    """描述"""
    discount = fields.FloatField(default=1)
    """折扣"""
    purchase_limit = fields.IntField(null=True, default=None)
    """每日限购"""
    use_limit = fields.IntField(null=True, default=None)
    """使用限制"""
    group = fields.JSONField(null=True, default=None)
    """商品组"""
    on_shelf = fields.BooleanField(default=True)

    class Meta:
        table = "goods_info"
        table_description = "商品信息"
