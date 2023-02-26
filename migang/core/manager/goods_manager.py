from typing import Callable, Optional, Dict, List
from pathlib import Path
import inspect
import asyncio

from pydantic import BaseModel
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, Event
from migang.core.models import GoodsInfo


class GoodsHandlerParams:
    def __init__(
        self,
        goods_name: str,
        user_id: int,
        group_id: Optional[int],
        bot: Bot,
        event: Event,
        num: int,
    ) -> None:
        self.goods_name: str = goods_name
        self.user_id: int = user_id
        self.group_id: Optional[int] = group_id
        self.bot: Bot = bot
        self.event: Event = event
        self.num: int = num


class Goods:
    def __init__(
        self,
        name: str,
        price: int,
        icon: Optional[Path] = None,
        discount: float = 1,
        daily_limit: Optional[int] = None,
        on_shelf: bool = True,
        description: str = "",
        passive: bool = False,
    ) -> None:
        self.name = name
        self.price = price
        self.icon = icon
        self.discount = discount
        self.daily_limit = daily_limit
        self.passive = passive
        self.on_shelf = on_shelf
        self.description = description
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
        for key, value in handler_params.__dict__:
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
        return self.__handle(0, handler_params=handler_params)

    async def handle(self, handler_params: GoodsHandlerParams) -> Optional[str]:
        """使用时调用

        Args:
            handler_params (GoodsHandlerParams): 各种参数

        Returns:
            Optional[str]: 若有句子要发，返回str
        """
        return self.__handle(1, handler_params=handler_params)

    async def after_handle(self, handler_params: GoodsHandlerParams) -> Optional[str]:
        """使用后调用

        Args:
            handler_params (GoodsHandlerParams): 各种参数

        Returns:
            Optional[str]: 若有句子要发，返回str
        """
        return self.__handle(2, handler_params=handler_params)


class GoodsManager:
    def __init__(self) -> None:
        self.__data: Dict[str, Goods] = {}

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

    def get_good(self, name: str) -> Optional[Goods]:
        """获取特定商品

        Args:
            name (str): 商品名

        Returns:
            Optional[Goods]: _description_
        """
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
            if goods_info := await GoodsInfo.filter(goods_name=goods).first():
                goods = self.__data[goods]
                (
                    goods.price,
                    goods.description,
                    goods.discount,
                    goods.daily_limit,
                    goods.on_shelf,
                ) = (
                    goods_info.price,
                    goods_info.description,
                    goods_info.discount,
                    goods_info.daily_limit,
                    goods_info.on_shelf,
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
            if goods_info := await GoodsInfo.filter(goods_name=goods).first():
                (
                    goods_info.price,
                    goods_info.description,
                    goods_info.discount,
                    goods_info.daily_limit,
                    goods_info.on_shelf,
                ) = (
                    goods.price,
                    goods.description,
                    goods.discount,
                    goods.daily_limit,
                    goods.on_shelf,
                )
                await goods_info.save()
            else:
                await GoodsInfo(
                    name=goods.name,
                    price=goods.price,
                    description=goods.description,
                    discount=goods.discount,
                    daily_limit=goods.daily_limit,
                    on_shelf=goods.on_shelf,
                ).save()
