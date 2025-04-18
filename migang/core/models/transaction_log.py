from typing import Tuple
from datetime import datetime

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Sum


class TransactionLog(Model):
    user_id = fields.BigIntField(null=False)
    gold_earned = fields.BigIntField(null=False, default=0)
    gold_spent = fields.BigIntField(null=False, default=0)
    description = fields.TextField(null=True)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "transaction_log"
        table_description = "交易日志"

    @classmethod
    async def get_gold_info(cls, user_id: int) -> Tuple[int, int, int, int]:
        """_summary_

        Args:
            user_id (int): _description_

        Returns:
            Tuple[int, int,int,int]: 今日获得，今日消耗，总获得，总消耗
        """
        today_data = (
            await cls.filter(
                user_id=user_id,
                time__gte=datetime.now()
                .astimezone()
                .replace(hour=0, minute=0, second=0, microsecond=0),
            )
            .annotate(today_earned=Sum("gold_earned"), today_spent=Sum("gold_spent"))
            .first()
            .values_list("today_earned", "today_spent")
        )
        total_date = (
            await cls.filter(user_id=user_id)
            .annotate(total_earned=Sum("gold_earned"), total_spent=Sum("gold_spent"))
            .first()
            .values_list("total_earned", "total_spent")
        )
        return (
            today_data[0] or 0,
            today_data[1] or 0,
            total_date[0] or 0,
            total_date[1] or 0,
        )
