from typing import Optional
from datetime import datetime
from enum import IntEnum, unique

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Sum
from tortoise.backends.base.client import BaseDBAsyncClient


@unique
class DepositType(IntEnum):
    demand_deposit: int = 0
    time_deposit: int = 1


class Bank(Model):
    user_id = fields.BigIntField(null=False)
    amount = fields.IntField(null=False, default=0)
    time = fields.DatetimeField(auto_now_add=True)
    deposit_type = fields.IntEnumField(
        enum_type=DepositType, default=DepositType.demand_deposit
    )
    duration = fields.DatetimeField(null=True, default=None)

    class Meta:
        table = "bank"
        table_description = "银行"

    @classmethod
    async def get_total_demand_deposit(
        cls, user_id: int, connection: Optional[BaseDBAsyncClient] = None
    ):
        return (
            await cls.filter(user_id=user_id, deposit_type=DepositType.demand_deposit)
            .annotate(amount=Sum("amount"))
            .using_db(connection)
            .first()
            .values_list("amount")
        )[0] or 0
