from typing import Dict, List, Tuple, Optional

from tortoise import fields
from tortoise.models import Model


class Shop(Model):
    goods_name = fields.CharField(255, unique=True)
    """商品名称"""
    goods_price = fields.IntField()
    """价格"""
    goods_description = fields.TextField()
    """描述"""
    goods_discount = fields.FloatField(default=1)
    """折扣"""
    goods_limit_time = fields.BigIntField(default=0)
    """限时"""
    daily_limit = fields.IntField(default=0)
    """每日限购"""
    is_passive = fields.BooleanField(default=False)
    """是否为被动道具"""
    icon = fields.TextField(null=True)
    """图标路径"""

    class Meta:
        table = "shop"
        table_description = "商店商品"

    @classmethod
    async def add_goods(
        cls,
        goods_name: str,
        goods_price: int,
        goods_description: str,
        goods_discount: float = 1,
        goods_limit_time: int = 0,
        daily_limit: int = 0,
        is_passive: bool = False,
        icon: Optional[str] = None,
    ):
        """
        说明:
            添加商品
        参数:
            :param goods_name: 商品名称
            :param goods_price: 商品价格
            :param goods_description: 商品简介
            :param goods_discount: 商品折扣
            :param goods_limit_time: 商品限时
            :param daily_limit: 每日购买限制
            :param is_passive: 是否为被动道具
            :param icon: 图标
        """
        if not await cls.filter(goods_name=goods_name).first():
            await cls.create(
                goods_name=goods_name,
                goods_price=goods_price,
                goods_description=goods_description,
                goods_discount=goods_discount,
                goods_limit_time=goods_limit_time,
                daily_limit=daily_limit,
                is_passive=is_passive,
                icon=icon,
            )

    @classmethod
    async def delete_goods(cls, goods_name: str) -> bool:
        """
        说明:
            删除商品
        参数:
            :param goods_name: 商品名称
        """
        if goods := await cls.get_or_none(goods_name=goods_name):
            await goods.delete()
            return True
        return False

    @classmethod
    async def update_goods(
        cls,
        goods_name: str,
        goods_price: Optional[int] = None,
        goods_description: Optional[str] = None,
        goods_discount: Optional[float] = None,
        goods_limit_time: Optional[int] = None,
        daily_limit: Optional[int] = None,
        is_passive: Optional[bool] = None,
        icon: Optional[str] = None,
    ):
        """
        说明:
            更新商品信息
        参数:
            :param goods_name: 商品名称
            :param goods_price: 商品价格
            :param goods_description: 商品简介
            :param goods_discount: 商品折扣
            :param goods_limit_time: 商品限时时间
            :param daily_limit: 每日次数限制
            :param is_passive: 是否为被动
            :param icon: 图标
        """
        if goods := await cls.get_or_none(goods_name=goods_name):
            await cls.update_or_create(
                goods_name=goods_name,
                defaults={
                    "goods_price": goods_price or goods.goods_price,
                    "goods_description": goods_description or goods.goods_description,
                    "goods_discount": goods_discount or goods.goods_discount,
                    "goods_limit_time": goods_limit_time
                    if goods_limit_time is not None
                    else goods.goods_limit_time,
                    "daily_limit": daily_limit
                    if daily_limit is not None
                    else goods.daily_limit,
                    "is_passive": is_passive
                    if is_passive is not None
                    else goods.is_passive,
                    "icon": icon or goods.icon,
                },
            )

    @classmethod
    async def get_all_goods(cls) -> List["GoodsInfo"]:
        """
        说明:
            获得全部有序商品对象
        """
        query = await cls.all()
        id_lst = [x.id for x in query]
        goods_lst = []
        for _ in range(len(query)):
            min_id = min(id_lst)
            goods_lst.append([x for x in query if x.id == min_id][0])
            id_lst.remove(min_id)
        return goods_lst
