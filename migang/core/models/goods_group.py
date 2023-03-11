from tortoise import fields
from tortoise.models import Model


class GoodsGroup(Model):
    name: str = fields.CharField(255, unique=True)
    """商品名称"""
    purchase_limit: int = fields.IntField(null=True, default=None)
    """组共享每日限购"""
    use_limit: int = fields.IntField(null=True, default=None)
    """组共享使用限制"""

    class Meta:
        table = "goods_group"
        table_description = "商品组信息"
