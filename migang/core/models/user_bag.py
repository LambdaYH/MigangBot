from tortoise import fields
from tortoise.models import Model


class UserBag(Model):
    user_id = fields.BigIntField(null=False)
    item_name = fields.CharField(255, null=False)
    amount = fields.IntField(null=False, default=0)

    class Meta:
        table = "user_bag"
        table_description = "用户背包"
        unique_together = ("user_id", "item_name")

    @classmethod
    async def add_item(cls, user_id: int, item_name: str, amount: int = 1):
        """
        说明:
            增加道具
        参数:
            :param user_qq: qq号
            :param group_id: 所在群号
            :param name: 道具名称
            :param num: 道具数量
        """
        user, _ = await cls.get_or_create(user_id=user_id, item_name=item_name)
        user.amount += amount
        await user.save(update_fields=["amount"])

    @classmethod
    async def use_item(cls, user_id: int, item_name: str, amount: int = 1) -> bool:
        """
        说明:
            使用/删除 道具
        参数:
            :param user_qq: qq号
            :param group_id: 所在群号
            :param name: 道具名称
            :param num: 使用个数
        """
        user, _ = await cls.get_or_create(user_id=user_id, item_name=item_name)
        if user.amount < amount:
            return False
        user.amount -= amount
        await user.save(update_fields=["amount"])
        return True

    @classmethod
    async def check_item(cls, user_id: int, item_name: str, amount: int = 1) -> bool:
        """
        说明:
            使用 道具
        参数:
            :param user_qq: qq号
            :param group_id: 所在群号
            :param name: 道具名称
            :param num: 使用个数
        """
        user, _ = await cls.get_or_create(user_id=user_id, item_name=item_name)
        return user.amount >= amount

    @classmethod
    async def get_item(cls, user_id: int, item_name: str) -> bool:
        """看看有没有商品在

        Args:
            user_id (int): _description_
            item_name (str): _description_

        Returns:
            bool: _description_
        """
        user = await cls.filter(user_id=user_id, item_name=item_name).first()
        if not user or user.amount == 0:
            return False
        return True

    @classmethod
    async def get_item_list(cls, user_id: int):
        return await cls.filter(user_id=user_id).exclude(amount=0).order_by("id").all()

    @classmethod
    async def get_name_by_idx(cls, user_id: int, idx: int):
        property_list = await cls.get_item_list(user_id=user_id)
        if idx >= len(property_list):
            return None
        return property_list[idx].item_name
