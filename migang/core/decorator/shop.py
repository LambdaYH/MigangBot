from pathlib import Path
from typing import Any, Dict, Tuple, Union, Callable, Iterable

from migang.core.manager import goods_manager
from migang.core.manager.goods_manager import Goods

"""固有参数
goods_name   # 商品名
user_id      # 使用者id
group_id =   # 使用者群id（若有）
bot          # bot
event        # 事件
num          # 使用量
**kwargs     # 自己定义的，用于同时注册多个
"""


def uniform_value(value, len) -> Tuple:
    if isinstance(value, Iterable) and not isinstance(value, str):
        return value
    return tuple([value] * len)


class GoodsRegister:
    def __init__(self) -> None:
        pass

    def __register(
        self,
        name: Union[str, Iterable[str]],
        price: Union[int, Iterable[int]],
        description: Union[str, Iterable[str], None] = None,
        passive: Union[bool, Iterable[bool], None] = None,
        icon: Union[Iterable[str], str, None] = None,
        daily_limit: Union[int, Iterable[int], None] = None,
        on_shelf: Union[bool, Iterable[bool], None] = None,
        discount: Union[float, Iterable[float], None] = None,
    ):
        len_ = len(name)
        name = uniform_value(name, len_)
        price = uniform_value(price, len_)
        description = uniform_value(description, len_, "")
        discount = uniform_value(discount, len_, 1)
        on_shelf = uniform_value(on_shelf, len_, True)
        daily_limit = uniform_value(daily_limit, len_, None)
        passive = uniform_value(passive, len_, False)
        icon = uniform_value(icon, len_, None)
        for x in [price, description, discount, on_shelf, daily_limit, passive, icon]:
            if len(x) != len_:
                raise ValueError(f"商品{name}的handle参数数量不一致")
        for (
            name_,
            price_,
            description_,
            discount_,
            on_shelf_,
            daily_limit_,
            passive_,
            icon_,
        ) in zip(
            name,
            price,
            description,
            discount,
            on_shelf,
            daily_limit,
            passive,
            icon,
        ):
            goods = Goods(
                name=name_,
                price=price_,
                icon=icon_,
                discount=discount_,
                daily_limit=daily_limit_,
                on_shelf=on_shelf_,
                description=description_,
                passive=passive_,
            )
            goods_manager.add(goods)

    def handle(
        self,
        name: Union[str, Iterable[str]],
        price: Union[int, Iterable[int]],
        description: Union[str, Iterable[str], None] = None,
        passive: Union[bool, Iterable[bool], None] = None,
        icon: Union[Iterable[str], str, None] = None,
        daily_limit: Union[int, Iterable[int], None] = None,
        on_shelf: Union[bool, Iterable[bool], None] = None,
        discount: Union[float, Iterable[float], None] = None,
        kwargs: Union[Dict[str, Any], Iterable[Dict[str, Any]], None] = None,
    ):
        self.__register(
            name=name,
            price=price,
            description=description,
            discount=discount,
            on_shelf=on_shelf,
            daily_limit=daily_limit,
            passive=passive,
            icon=icon,
        )
        if isinstance(name, str):
            name = (name,)
        if kwargs is None:
            kwargs = len(name) * [{}]
        elif isinstance(kwargs, Dict):
            kwargs = [kwargs] * len(name)
        if len(kwargs) != len(name):
            raise ValueError(f"注册{name}的handle时，kwargs与商品数不一致")

        def register(func: Callable):
            for i, goods_name in enumerate(name):
                if goods := goods_manager.get_good(name=goods_name):
                    goods.register_handler(func, kwargs=kwargs[i])

        return register

    def before_handle(
        self,
        name: Union[str, Iterable[str]],
        price: Union[int, Iterable[int]],
        description: Union[str, Iterable[str], None] = None,
        passive: Union[bool, Iterable[bool], None] = None,
        icon: Union[Iterable[str], str, None] = None,
        daily_limit: Union[int, Iterable[int], None] = None,
        on_shelf: Union[bool, Iterable[bool], None] = None,
        discount: Union[float, Iterable[float], None] = None,
        kwargs: Union[Dict[str, Any], Iterable[Dict[str, Any]], None] = None,
    ):
        self.__register(
            name=name,
            price=price,
            description=description,
            discount=discount,
            on_shelf=on_shelf,
            daily_limit=daily_limit,
            passive=passive,
            icon=icon,
        )
        if isinstance(name, str):
            name = (name,)
        if kwargs is None:
            kwargs = len(name) * [{}]
        elif isinstance(kwargs, Dict):
            kwargs = [kwargs] * len(name)
        if len(kwargs) != len(name):
            raise ValueError(f"注册{name}的handle时，kwargs与商品数不一致")

        def register(func: Callable):
            for i, goods_name in enumerate(name):
                if goods := goods_manager.get_good(name=goods_name):
                    goods.register_before_handler(func, kwargs=kwargs[i])

        return register

    def after_handle(
        self,
        name: Union[str, Iterable[str]],
        price: Union[int, Iterable[int]],
        description: Union[str, Iterable[str], None] = None,
        passive: Union[bool, Iterable[bool], None] = None,
        icon: Union[Iterable[str], str, None] = None,
        daily_limit: Union[int, Iterable[int], None] = None,
        on_shelf: Union[bool, Iterable[bool], None] = None,
        discount: Union[float, Iterable[float], None] = None,
        kwargs: Union[Dict[str, Any], Iterable[Dict[str, Any]], None] = None,
    ):
        self.__register(
            name=name,
            price=price,
            description=description,
            discount=discount,
            on_shelf=on_shelf,
            daily_limit=daily_limit,
            passive=passive,
            icon=icon,
        )
        if isinstance(name, str):
            name = (name,)
        if kwargs is None:
            kwargs = len(name) * [{}]
        elif isinstance(kwargs, Dict):
            kwargs = [kwargs] * len(name)
        if len(kwargs) != len(name):
            raise ValueError(f"注册{name}的handle时，kwargs与商品数不一致")

        def register(func: Callable):
            for i, goods_name in enumerate(name):
                if goods := goods_manager.get_good(name=goods_name):
                    goods.register_after_handler(func, kwargs=kwargs[i])

        return register


goods_register = GoodsRegister()
