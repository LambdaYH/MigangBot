from typing import Optional
from datetime import datetime

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Sum
from tortoise.backends.base.client import BaseDBAsyncClient

TIMEDELTA = datetime.now() - datetime.utcnow()


class ShopGroupLog(Model):
    user_id = fields.BigIntField(null=False)
    group_name = fields.CharField(255, null=False)
    amount = fields.IntField(null=False)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "shop_group_log"
        table_description = "商品组购买/退货记录"

    @classmethod
    async def get_today_purchase_amount(
        cls,
        user_id: int,
        group_name: str,
        connection: Optional[BaseDBAsyncClient] = None,
    ) -> int:
        now = datetime.now()
        return (
            await cls.filter(
                user_id=user_id,
                group_name=group_name,
                time__gte=now.replace(hour=0, minute=0, second=0, microsecond=0)
                - TIMEDELTA,
            )
            .annotate(amount=Sum("amount"))
            .using_db(connection)
            .first()
            .values_list("amount")
        )[0] or 0
