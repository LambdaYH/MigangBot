from datetime import datetime, timedelta
from tortoise import fields
from tortoise.functions import Sum
from tortoise.models import Model

TIMEDELTA = datetime.now() - datetime.utcnow()


class ShopLog(Model):
    user_id = fields.BigIntField(null=False)
    item_name = fields.CharField(255, null=False)
    amount = fields.IntField(null=False)
    price = fields.FloatField(null=False)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "shop_log"
        table_description = "商店购买/退货记录"
        unique_together = ("user_id", "item_name")

    @classmethod
    async def get_today_purchase_amount(cls, user_id: int, item_name: str) -> int:
        now = datetime.now()
        await cls.filter(
            user_id=user_id,
            item_name=item_name,
            time__range=(
                datetime.now()
                - timedelta(
                    hours=now.hour,
                    minutes=now.minute,
                    seconds=now.second,
                    microseconds=now.microsecond,
                )
                - TIMEDELTA,
                now - TIMEDELTA,
            ),
        ).annotate(amount=Sum("amount")).first().values_list("amount")[0]
