from typing import Optional
from datetime import datetime

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Sum
from tortoise.backends.base.client import BaseDBAsyncClient


class ShopLog(Model):
    user_id = fields.BigIntField(null=False)
    item_name = fields.CharField(255, null=False)
    amount = fields.BigIntField(null=False)
    price = fields.FloatField(null=False)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "shop_log"
        table_description = "商店购买/退货记录"

    @classmethod
    async def get_today_purchase_amount(
        cls,
        user_id: int,
        item_name: str,
        connection: Optional[BaseDBAsyncClient] = None,
    ) -> int:
        return (
            await cls.filter(
                user_id=user_id,
                item_name=item_name,
                time__gte=datetime.now()
                .astimezone()
                .replace(hour=0, minute=0, second=0, microsecond=0),
            )
            .annotate(amount=Sum("amount"))
            .using_db(connection)
            .first()
            .values_list("amount")
        )[0] or 0
