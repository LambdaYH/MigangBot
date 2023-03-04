from typing import Union, Optional
from decimal import Decimal
import sys
from pathlib import Path

from tortoise import fields
from tortoise.models import Model
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from migang.core.models.transaction_log import TransactionLog


class UserProperty(Model):
    user_id = fields.BigIntField(pk=True)
    nickname = fields.TextField(null=True, default=None)
    gold = fields.BigIntField(null=False, default=0)
    impression = fields.DecimalField(12, 3, default=0)

    class Meta:
        table = "user_property"
        table_description = "与用户相关的各项可变动属性记录"

    async def modify_gold(
        self,
        gold_diff: int,
        description: Optional[str] = None,
        connection: Optional[BaseDBAsyncClient] = None,
    ):
        self.gold += gold_diff
        if not description:
            file_path = Path(sys._getframe(1).f_code.co_filename)
            description = f"由 {file_path} 调用"
        if gold_diff >= 0:
            await TransactionLog(
                user_id=self.user_id, gold_earned=gold_diff, desciption=description
            ).save(using_db=connection)
        else:
            await TransactionLog(
                user_id=self.user_id, gold_spent=-gold_diff, desciption=description
            ).save(using_db=connection)
        await self.save(update_fields=["gold"], using_db=connection)

    async def modify_impression(self, impression_diff: Union[Decimal, float]):
        if isinstance(impression_diff, float):
            impression_diff = Decimal(impression_diff)
        self.impression += impression_diff
        await self.save(update_fields=["impression"])

    @classmethod
    async def modify_gold(
        cls, user_id: int, gold_diff: int, description: Optional[str] = None
    ):
        if not description:
            file_path = Path(sys._getframe(1).f_code.co_filename)
            description = f"由 {file_path} 调用"
        async with in_transaction() as connection:
            user = await cls.filter(user_id=user_id).using_db(connection).first()
            if not user:
                user = await cls(user_id=user_id).save(using_db=connection)
            user.gold += gold_diff
            if gold_diff >= 0:
                await TransactionLog(
                    user_id=user_id, gold_earned=gold_diff, desciption=description
                ).save(using_db=connection)
            else:
                await TransactionLog(
                    user_id=user_id, gold_spent=-gold_diff, desciption=description
                ).save(using_db=connection)
            await user.save(update_fields=["gold"], using_db=connection)

    @classmethod
    async def modify_impression(
        cls, user_id: int, impression_diff: Union[Decimal, float]
    ):
        user = await cls.filter(user_id=user_id).first()
        if not user:
            user = cls(user_id=user_id)
        if isinstance(impression_diff, float):
            impression_diff = Decimal(impression_diff)
        user.impression += impression_diff
        await user.save(update_fields=["impression"])

    @classmethod
    async def get_gold(cls, user_id: int) -> None:
        user = await cls.filter(user_id=user_id).first()
        if not user:
            return 0
        return user.gold
