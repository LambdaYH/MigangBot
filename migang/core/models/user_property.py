from typing import Union
from decimal import Decimal

from tortoise import fields
from tortoise.models import Model


class UserProperty(Model):
    user_id = fields.BigIntField(pk=True)
    nickname = fields.TextField(null=True, default=None)
    gold = fields.BigIntField(null=False, default=0)
    impression = fields.DecimalField(12, 3, default=0)

    class Meta:
        table = "user_property"
        table_description = "与用户相关的各项可变动属性记录"

    async def modify_gold(self, gold_diff: int):
        self.gold += gold_diff
        await self.save(update_fields=["gold"])

    async def modify_impression(self, impression_diff: Union[Decimal, float]):
        if isinstance(impression_diff, float):
            impression_diff = Decimal(impression_diff)
        self.impression += impression_diff
        await self.save(update_fields=["impression"])

    @classmethod
    async def modify_gold(cls, user_id: int, gold_diff: int):
        user = await cls.filter(user_id=user_id).first()
        if not user:
            user = cls(user_id=user_id)
        user.gold += gold_diff
        await user.save(update_fields=["gold"])

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
    async def get_gold(cls, user_id:int) -> None:
        user = await cls.filter(user_id=user_id).first()
        if not user:
            return 0
        return user.gold
