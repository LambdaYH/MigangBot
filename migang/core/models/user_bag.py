from typing import List, Optional

from tortoise import fields
from tortoise.models import Model
from tortoise.backends.base.client import BaseDBAsyncClient

from migang.core.constant import ID_MAX_LENGTH


class UserBag(Model):
    user_id = fields.CharField(max_length=ID_MAX_LENGTH, null=False)
    item_name = fields.CharField(255, null=False)
    amount = fields.IntField(null=False, default=0)

    class Meta:
        table = "user_bag"
        table_description = "用户背包"
        unique_together = ("user_id", "item_name")

    @classmethod
    async def add_item(
        cls,
        user_id: int,
        item_name: str,
        amount: int = 1,
        connection: Optional[BaseDBAsyncClient] = None,
    ):
        """添加道具

        Args:
            user_id (int): 用户id
            item_name (str): 道具名
            amount (int, optional): 数量. Defaults to 1.
            connection (Optional[BaseDBAsyncClient], optional): 事务连接. Defaults to None.
        """
        user, _ = await cls.get_or_create(
            user_id=user_id, item_name=item_name, using_db=connection
        )
        user.amount += amount
        await user.save(update_fields=["amount"], using_db=connection)

    @classmethod
    async def del_item(
        cls,
        user_id: int,
        item_name: str,
        amount: int = 1,
        connection: Optional[BaseDBAsyncClient] = None,
    ):
        """删除道具

        Args:
            user_id (int): 用户id
            item_name (str): 道具名
            amount (int, optional): 数量. Defaults to 1.
            connection (Optional[BaseDBAsyncClient], optional): 事务连接. Defaults to None.
        """
        user, _ = await cls.get_or_create(
            user_id=user_id, item_name=item_name, using_db=connection
        )
        user.amount -= amount
        user.amount = max(0, user.amount)
        await user.save(update_fields=["amount"], using_db=connection)

    @classmethod
    async def check_item(
        cls,
        user_id: int,
        item_name: str,
        amount: int = 1,
        connection: Optional[BaseDBAsyncClient] = None,
    ) -> bool:
        """检查道具，若能够使用返回True

        Args:
            user_id (int): 用户id
            item_name (str): 道具名
            amount (int, optional): 数量. Defaults to 1.
            connection (Optional[BaseDBAsyncClient], optional): 事务连接. Defaults to None.

        Returns:
            bool: 若能够使用，返回True
        """
        user, _ = await cls.get_or_create(
            user_id=user_id, item_name=item_name, using_db=connection
        )
        return user.amount >= amount

    @classmethod
    async def get_item(cls, user_id: int, item_name: str) -> bool:
        """看看有没有道具在

        Args:
            user_id (int): 用户id
            item_name (str): 道具名

        Returns:
            bool: 若存在，返回True
        """
        user = await cls.filter(user_id=user_id, item_name=item_name).first()
        if not user or user.amount == 0:
            return False
        return True

    @classmethod
    async def get_item_list(cls, user_id: int) -> List["UserBag"]:
        """获取用户背包的道具

        Args:
            user_id (int): 用户id

        Returns:
            List[UserBag]: 背包中的道具
        """
        return await cls.filter(user_id=user_id).exclude(amount=0).order_by("id").all()
