from typing import Any, Dict, Tuple, Union, Callable, Iterable, Optional

from migang.core.manager import goods_manager
from migang.core.manager.goods_manager import (  # noqa
    Goods,
    GoodsGroup,
    CancelGoodsHandle,
    CancelThisGoodsHandle,
)

"""固有参数
goods_name   # 商品名
user_id      # 使用者id
group_id =   # 使用者群id（若有）
bot          # bot
event        # 事件
num          # 使用量
**kwargs     # 自己定义的，用于同时注册多个
"""


def uniform_value(value, len_, default_value=None) -> Tuple:
    if value is None:
        return [default_value] * len_
    if isinstance(value, Iterable) and not isinstance(value, str):
        return value
    return tuple([value] * len_)


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
        purchase_limit: Union[int, Iterable[int], None] = None,
        use_limit: Union[int, Iterable[int], None] = None,
        single_use_limit: Union[int, Iterable[int], None] = None,
        on_shelf: Union[bool, Iterable[bool], None] = None,
        consumable: Union[bool, Iterable[bool], None] = None,
        discount: Union[float, Iterable[float], None] = None,
        group: Union[str, Iterable[str], Iterable[Tuple], None] = None,
    ):
        if isinstance(name, str):
            name = (name,)
        len_ = len(name)
        name = uniform_value(name, len_)
        price = uniform_value(price, len_)
        description = uniform_value(description, len_, "")
        discount = uniform_value(discount, len_, 1)
        on_shelf = uniform_value(on_shelf, len_, True)
        consumable = uniform_value(consumable, len_, True)
        purchase_limit = uniform_value(purchase_limit, len_, None)
        use_limit = uniform_value(use_limit, len_, None)
        single_use_limit = uniform_value(single_use_limit, len_, 1)
        passive = uniform_value(passive, len_, False)
        icon = uniform_value(icon, len_, None)
        if group is None:
            group = [None] * len_
        else:
            if isinstance(group, str):
                group = [group] * len_
            new_group = []
            for g in group:
                if isinstance(g, str):
                    new_group.append((g,))
                else:
                    new_group.append(g)
            group = new_group
        for x in [
            price,
            description,
            consumable,
            discount,
            on_shelf,
            purchase_limit,
            use_limit,
            single_use_limit,
            passive,
            icon,
            group,
        ]:
            if len(x) != len_:
                raise ValueError(f"商品{name}的handle参数数量不一致")
        for (
            name_,
            price_,
            description_,
            consumable_,
            discount_,
            on_shelf_,
            purchase_limit_,
            use_limit_,
            single_use_limit_,
            passive_,
            icon_,
            group_,
        ) in zip(
            name,
            price,
            description,
            consumable,
            discount,
            on_shelf,
            purchase_limit,
            use_limit,
            single_use_limit,
            passive,
            icon,
            group,
        ):
            goods = Goods(
                name=name_,
                price=price_,
                icon=icon_,
                discount=discount_,
                purchase_limit=purchase_limit_,
                use_limit=use_limit_,
                single_use_limit=single_use_limit_,
                consumable=consumable_,
                on_shelf=on_shelf_,
                description=description_,
                passive=passive_,
                group=group_,
            )
            goods_manager.add(goods)

    def __call__(
        self,
        name: Union[str, Iterable[str]],
        price: Union[int, Iterable[int]],
        description: Union[str, Iterable[str], None] = None,
        passive: Union[bool, Iterable[bool], None] = None,
        icon: Union[Iterable[str], str, None] = None,
        purchase_limit: Union[int, Iterable[int], None] = None,
        use_limit: Union[int, Iterable[int], None] = None,
        single_use_limit: Union[int, Iterable[int], None] = None,
        on_shelf: Union[bool, Iterable[bool], None] = None,
        consumable: Union[bool, Iterable[bool], None] = None,
        discount: Union[float, Iterable[float], None] = None,
        group: Union[str, Iterable[str], Iterable[Tuple], None] = None,
        kwargs: Union[Dict[str, Any], Iterable[Dict[str, Any]], None] = None,
    ):
        self.__register(
            name=name,
            price=price,
            description=description,
            discount=discount,
            on_shelf=on_shelf,
            purchase_limit=purchase_limit,
            use_limit=use_limit,
            single_use_limit=single_use_limit,
            consumable=consumable,
            passive=passive,
            icon=icon,
            group=group,
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
                if goods := goods_manager.get_goods(name=goods_name):
                    goods.register_handler(func, kwargs=kwargs[i])

        return register

    def before_handle(
        self,
        name: Union[str, Iterable[str]],
        kwargs: Union[Dict[str, Any], Iterable[Dict[str, Any]], None] = None,
    ):
        if isinstance(name, str):
            name = (name,)
        if kwargs is None:
            kwargs = len(name) * [{}]
        elif isinstance(kwargs, Dict):
            kwargs = [kwargs] * len(name)
        if len(kwargs) != len(name):
            raise ValueError(f"注册{name}的before_handle时，kwargs与商品数不一致")

        def register(func: Callable):
            for i, goods_name in enumerate(name):
                if goods := goods_manager.get_goods(name=goods_name):
                    goods.register_before_handler(func, kwargs=kwargs[i])

        return register

    def after_handle(
        self,
        name: Union[str, Iterable[str]],
        kwargs: Union[Dict[str, Any], Iterable[Dict[str, Any]], None] = None,
    ):
        if isinstance(name, str):
            name = (name,)
        if kwargs is None:
            kwargs = len(name) * [{}]
        elif isinstance(kwargs, Dict):
            kwargs = [kwargs] * len(name)
        if len(kwargs) != len(name):
            raise ValueError(f"注册{name}的after_handle时，kwargs与商品数不一致")

        def register(func: Callable):
            for i, goods_name in enumerate(name):
                if goods := goods_manager.get_goods(name=goods_name):
                    goods.register_after_handler(func, kwargs=kwargs[i])

        return register

    def register_group(
        self,
        name: str,
        discount: float = 1,
        purchase_limit: Optional[int] = None,
        use_limit: Optional[int] = None,
        on_shelf: bool = True,
    ):
        goods_manager.add_group(
            name=name,
            goods_group=GoodsGroup(
                name=name,
                discount=discount,
                purchase_limit=purchase_limit,
                use_limit=use_limit,
                on_shelf=on_shelf,
            ),
        )


goods_register = GoodsRegister()
