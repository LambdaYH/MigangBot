import asyncio
import inspect
from pathlib import Path
from enum import IntEnum, unique
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Union, Callable, Optional

from nonebot.log import logger
from tortoise.functions import Sum
from nonebot.matcher import Matcher
from tortoise.transactions import in_transaction
from nonebot.adapters.onebot.v11 import Bot, Event

from migang.core.models import UserBag, GoodsInfo, GoodsUseLog


class CancelThisGoodsHandle(Exception):
    """取消本个调用函数"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_


class CancelGoodsHandle(Exception):
    """取消本次商品使用"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_


class GoodsHandlerParams:
    def __init__(
        self,
        goods_name: str,
        user_id: int,
        group_id: Optional[int],
        bot: Bot,
        event: Event,
        matcher: Matcher,
        num: int,
    ) -> None:
        """方便写用的，在调用商品处理函数时候方便传过去

        Args:
            goods_name (str): 商品名
            user_id (int): 用户id
            group_id (Optional[int]): 群id，可以没有
            bot (Bot): 机器人
            event (Event): 时间
            num (int): 数量
        """
        self.goods_name: str = goods_name
        self.user_id: int = user_id
        self.group_id: Optional[int] = group_id
        self.bot: Bot = bot
        self.event: Event = event
        self.matcher: Matcher = matcher
        self.num: int = num


class GoodsGroup:
    def __init__(
        self,
        name: str,
        discount: Optional[float] = 1,
        purchase_limit: Optional[int] = None,
        use_limit: Optional[int] = None,
        on_shelf: Optional[bool] = True,
    ) -> None:
        """商品组，当对组操作时，组内为None的属性表示不共享

        Args:
            name (str): 组名
            discount (Optional[float], optional): 折扣. Defaults to 1.
            purchase_limit (Optional[int], optional): 购买限制. Defaults to None.
            use_limit (Optional[int], optional): 使用限制. Defaults to None.
            on_shelf (Optional[bool], optional): 商品是否上架. Defaults to True.
        """
        self.name = name
        self.discount = discount
        self.purchase_limit = purchase_limit
        self.use_limit = use_limit
        self.on_shelf = on_shelf

    def check_use_limit(self, amount: int) -> bool:
        """检查是否达到使用量限制

        Args:
            amount (int): 当日使用量

        Returns:
            bool: 若未达到，返回True
        """
        return (self.use_limit is None) or (amount <= self.use_limit)

    def check_purchase_limit(self, amount: int) -> bool:
        """检查是否达到购买量限制

        Args:
            amount (int): 当日购买量

        Returns:
            bool: 若未达到，返回True
        """
        return (self.purchase_limit is None) or (amount <= self.purchase_limit)


class Goods:
    """单个商品"""

    def __init__(
        self,
        name: str,
        price: int,
        icon: Optional[Path] = None,
        discount: float = 1,
        purchase_limit: Optional[int] = None,
        use_limit: Optional[int] = None,
        single_use_limit: int = 1,
        on_shelf: bool = True,
        consumable: bool = True,
        description: str = "",
        passive: bool = False,
        group: Optional[Tuple[str]] = None,
    ) -> None:
        self.name = name
        self.price = price
        self.icon = icon
        self.discount = discount
        self.purchase_limit = purchase_limit
        self.use_limit = use_limit
        self.single_use_limit = single_use_limit
        self.passive = passive
        self.on_shelf = on_shelf
        self.consumable = consumable
        self.description = description
        self.group = group
        self.__handlers = [None, None, None]
        self.__kwargs = [{}, {}, {}]

    def __register_handler(
        self, func_id: int, handler: Callable[..., Optional[str]], kwargs: Dict = {}
    ):
        self.__handlers[func_id] = handler
        self.__kwargs[func_id] = kwargs

    def register_before_handler(
        self, handler: Callable[..., Optional[str]], kwargs: Dict = {}
    ):
        self.__register_handler(0, handler=handler, kwargs=kwargs)

    def register_handler(
        self, handler: Callable[..., Optional[str]], kwargs: Dict = {}
    ):
        self.__register_handler(1, handler=handler, kwargs=kwargs)

    def register_after_handler(
        self, handler: Callable[..., Optional[str]], kwargs: Dict = {}
    ):
        self.__register_handler(2, handler=handler, kwargs=kwargs)

    async def __handle(
        self, func_id: int, handler_params: GoodsHandlerParams
    ) -> Optional[str]:
        if func_id < 0 or func_id >= len(self.__handlers):
            return None
        func = self.__handlers[func_id]
        if func is None:
            return None
        params_required = inspect.signature(func).parameters
        given_parmas = {}
        for key, value in handler_params.__dict__.items():
            if key in params_required:
                given_parmas[key] = value
        return (
            await func(**given_parmas, **self.__kwargs[func_id])
            if asyncio.iscoroutinefunction(func)
            else func(**given_parmas, **self.__kwargs[func_id])
        )

    async def before_handle(self, handler_params: GoodsHandlerParams) -> Optional[str]:
        """使用前调用

        Args:
            handler_params (GoodsHandlerParams): 各种参数

        Returns:
            Optional[str]: 若有句子要发，返回str
        """
        return await self.__handle(0, handler_params=handler_params)

    async def handle(self, handler_params: GoodsHandlerParams) -> Optional[str]:
        """使用时调用

        Args:
            handler_params (GoodsHandlerParams): 各种参数

        Returns:
            Optional[str]: 若有句子要发，返回str
        """
        return await self.__handle(1, handler_params=handler_params)

    async def after_handle(self, handler_params: GoodsHandlerParams) -> Optional[str]:
        """使用后调用

        Args:
            handler_params (GoodsHandlerParams): 各种参数

        Returns:
            Optional[str]: 若有句子要发，返回str
        """
        return await self.__handle(2, handler_params=handler_params)

    def check_use_limit(self, amount: int) -> bool:
        """检查是否达到使用量限制

        Args:
            amount (int): 当日使用量

        Returns:
            bool: 若未达到，返回True
        """
        return (self.use_limit is None) or (amount <= self.use_limit)

    def check_purchase_limit(self, amount: int) -> bool:
        """检查是否达到购买量限制

        Args:
            amount (int): 当日购买量

        Returns:
            bool: 若未达到，返回True
        """
        return (self.purchase_limit is None) or (amount <= self.purchase_limit)

    def check_single_use_limit(self, amount: int) -> bool:
        return amount <= self.single_use_limit


@unique
class UseStatus(IntEnum):
    NO_SUCH_ITEM_IN_BAG: int = 0
    """背包中无该物品"""
    INSUFFICIENT_QUANTITY: int = 1
    """物品数量不足"""
    USE_LIMIT: int = 2
    """物品达到使用限制"""
    GROUP_USE_LIMIT: int = 3
    """该组物品达到使用限制"""
    ITEM_DISABLED: int = 4
    """该物品已禁用"""
    SUCCESS: int = 5
    """使用成功"""
    NO_SUCH_GOODS: int = 6
    """没有这种商品"""
    CANCELLED: int = 7
    """本次使用被取消了"""
    SINGLE_USE_LIMIT: int = 8
    """达到单次使用限制"""


TIMEDELTA = datetime.now() - datetime.utcnow()


class GoodsManager:
    def __init__(self) -> None:
        self.__data: Dict[str, Goods] = {}
        self.__goods_group: Dict[str, GoodsGroup] = {}

    async def init(self) -> None:
        """初始化"""
        await self.load_from_db()
        for goods in self.__data.values():
            if goods.group and (goods_group := self.__goods_group.get(goods.group)):
                goods.discount, goods.on_shelf = (
                    goods_group.discount,
                    goods_group.on_shelf,
                )

    async def use_goods(
        self, user_id: int, name: Union[str, int], params: GoodsHandlerParams
    ) -> Tuple[UseStatus, Optional[Dict[str, Any]]]:
        async with in_transaction() as connection:
            if isinstance(name, int):
                user_bag_items = (
                    await UserBag.filter(user_id=user_id)
                    .exclude(amount=0)
                    .order_by("id")
                    .all()
                )
                if name <= 0 or name > len(user_bag_items):
                    return UseStatus.NO_SUCH_ITEM_IN_BAG, None
                user = user_bag_items[name - 1]
                params.goods_name = name = user.item_name
            else:
                user = (
                    await UserBag.filter(user_id=user_id, item_name=name)
                    .using_db(connection)
                    .first()
                )
            if not user or user.amount == 0:
                if name not in self.__data:
                    return UseStatus.NO_SUCH_GOODS, None
                return UseStatus.NO_SUCH_ITEM_IN_BAG, None
            amount = params.num
            goods = self.__data.get(name)
            if not goods:
                return UseStatus.ITEM_DISABLED, None
            if goods.single_use_limit < amount:
                return UseStatus.SINGLE_USE_LIMIT, {"count": goods.single_use_limit}
            if user.amount < amount:
                return UseStatus.INSUFFICIENT_QUANTITY, {"count": user.amount}
            now = datetime.now()
            today_data = (
                await GoodsUseLog.filter(
                    user_id=user_id,
                    goods_name=name,
                    time__gte=now
                    - timedelta(
                        hours=now.hour,
                        minutes=now.minute,
                        seconds=now.second,
                        microseconds=now.microsecond,
                    )
                    - TIMEDELTA,
                )
                .annotate(today_used=Sum("amount"))
                .using_db(connection)
                .first()
                .values_list("today_used")
            )
            today_use = today_data[0] or 0
            if not goods.check_use_limit(today_use + amount):
                return UseStatus.USE_LIMIT, {"count": goods.use_limit - today_use}
            if goods.group:
                for group in goods.group:
                    if (
                        goods_group := self.__goods_group.get(group)
                    ) and not goods_group.check_use_limit(today_use + amount):
                        return (
                            UseStatus.GROUP_USE_LIMIT,
                            {"count": goods_group.use_limit - today_use},
                        )
            matcher = params.matcher
            try:
                try:
                    if ret := await goods.before_handle(params):
                        await matcher.send(ret, at_sender=True)
                except CancelThisGoodsHandle:
                    pass
                try:
                    if ret := await goods.handle(params):
                        await matcher.send(ret, at_sender=True)
                except CancelThisGoodsHandle:
                    pass
                try:
                    if ret := await goods.after_handle(params):
                        await matcher.send(ret, at_sender=True)
                except CancelThisGoodsHandle:
                    pass
                if goods.consumable:
                    user.amount -= amount
                await GoodsUseLog(user_id=user_id, goods_name=name, amount=amount).save(
                    using_db=connection
                )
                await user.save(update_fields=["amount"], using_db=connection)
                return UseStatus.SUCCESS, {"name": name, "count": amount}
            except CancelGoodsHandle as e:
                return UseStatus.CANCELLED, {"reason": str(e)}

    def add(self, goods: Goods) -> None:
        """添加商品

        Args:
            goods (Goods): 商品
        """
        if goods.name in self.__data:
            logger.warning(f"商品 {goods.name} 重复添加")
        self.__data[goods.name] = goods

    def get_all_goods(self) -> List[Goods]:
        """获取所有已注册商品

        Returns:
            List[Goods]: _description_
        """
        return self.__data.values()

    def get_all_goods_on_shelves(self) -> List[Goods]:
        """获取上架了的商品

        Returns:
            List[Goods]: _description_
        """
        return [goods for goods in self.__data.values() if goods.on_shelf]

    def get_goods(self, name: Union[str, int]) -> Optional[Goods]:
        """获取特定商品

        Args:
            name (Union[str, int]): 商品名或序号

        Returns:
            Optional[Goods]: _description_
        """
        if isinstance(name, int):
            if name < 0 or name >= len(self.__data):
                return None
            return list(self.__data.values())[name]
        return self.__data.get(name)

    async def adjust(self, name: str, **kwargs) -> None:
        """调整商品价格折扣等，数据库中存储的项

        Args:
            name (str): 商品名
        """
        goods = self.__data.get(name)
        if not goods:
            return
        for key, v in kwargs:
            if key in goods.__dict__:
                goods.__dict__[key] = v
        await self.save_to_db(name=name)

    def add_group(self, name: str, goods_group: GoodsGroup) -> None:
        """把一个商品组添加进来

        Args:
            name (str): _description_
            goods_group (GoodsGroup): _description_
        """
        self.__goods_group[name] = goods_group

    async def load_from_db(self, name: Optional[str] = None) -> None:
        """所有商品属性以数据库中为准

        Args:
            name (Optional[str], optional): 商品名，若空则全部商品. Defaults to None.
        """
        if name:
            name = (name,)
        else:
            name = self.__data.keys()
        for goods in name:
            if goods_info := await GoodsInfo.filter(name=goods).first():
                goods = self.__data[goods]
                (
                    goods.price,
                    goods.description,
                    goods.discount,
                    goods.purchase_limit,
                    goods.use_limit,
                    goods.on_shelf,
                    goods.group,
                ) = (
                    goods_info.price,
                    goods_info.description,
                    goods_info.discount,
                    goods_info.purchase_limit,
                    goods_info.use_limit,
                    goods_info.on_shelf,
                    goods_info.group,
                )

    async def save_to_db(self, name: Optional[str] = None) -> None:
        """将商品数据写入数据库

        Args:
            name (Optional[str], optional): 商品名，若空则全部商品. Defaults to None.
        """
        if name:
            name = (name,)
        else:
            name = self.__data.keys()
        for goods in name:
            goods = self.__data[goods]
            if goods_info := await GoodsInfo.filter(name=goods).first():
                (
                    goods_info.price,
                    goods_info.description,
                    goods_info.discount,
                    goods_info.purchase_limit,
                    goods_info.on_shelf,
                ) = (
                    goods.price,
                    goods.description,
                    goods.discount,
                    goods.purchase_limit,
                    goods.on_shelf,
                )
                await goods_info.save()
            else:
                await GoodsInfo(
                    name=goods.name,
                    price=goods.price,
                    description=goods.description,
                    discount=goods.discount,
                    purchase_limit=goods.purchase_limit,
                    on_shelf=goods.on_shelf,
                ).save()
