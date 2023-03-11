from typing import List
from tortoise import fields
from tortoise.models import Model


class GoodsInfo(Model):
    name: str = fields.CharField(255, unique=True)
    """商品名称"""
    price: int = fields.IntField()
    """价格"""
    description: str = fields.TextField()
    """描述"""
    discount: float = fields.FloatField(default=1)
    """折扣"""
    purchase_limit: int = fields.IntField(null=True, default=None)
    """每日限购"""
    use_limit: int = fields.IntField(null=True, default=None)
    """使用限制"""
    group: List[str] = fields.JSONField(null=True, default=None)
    """商品组"""
    on_shelf: bool = fields.BooleanField(default=True)

    class Meta:
        table = "goods_info"
        table_description = "商品信息"
