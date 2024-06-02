from datetime import datetime

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Sum


class GoodsUseLog(Model):
    user_id = fields.BigIntField(null=False)
    goods_name = fields.TextField(null=False)
    amount = fields.BigIntField(null=False, default=1)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "goods_use_log"
        table_description = "商品使用日志"

    @classmethod
    async def get_today_use(cls, user_id: int, goods_name: str) -> int:
        """_summary_

        Args:
            user_id (int): _description_

        Returns:
            Tuple[int, int,int,int]: 今日获得，今日消耗，总获得，总消耗
        """
        today_data = (
            await cls.filter(
                user_id=user_id,
                goods_name=goods_name,
                time__gte=datetime.now()
                .astimezone()
                .replace(hour=0, minute=0, second=0, microsecond=0),
            )
            .annotate(today_used=Sum("amount"))
            .first()
            .values_list("today_used")
        )
        return today_data[0] or 0
