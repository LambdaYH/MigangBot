import random
import inspect
from asyncio import iscoroutinefunction
from typing import Any, Dict, List, Tuple, Union, Callable, Optional, Coroutine

from nonebot.log import logger

from migang.core.models import SignIn, UserProperty


class Effect:
    def __init__(
        self,
        name: str,
        func: Callable[
            [int, SignIn, UserProperty],
            Union[
                Union[str, Coroutine[Any, Any, str]],
                Tuple[Union[str, Coroutine[Any, Any, str]], Optional[Dict[str, Any]]],
            ],
        ],
    ) -> None:
        self.name = name
        self.func = func
        self.next_func: Optional[
            Callable[..., Union[str, Coroutine[Any, Any, str]]]
        ] = None

    async def __call__(
        self, user_id: int, user_sign_in: SignIn, user_prop: UserProperty
    ) -> Union[str, Tuple[str, Optional[Dict[str, Any]]]]:
        """当该效果存在第二个返回值时，需要返回下一次调用所需的参数，以Dict形式返回

        Args:
            user_id (int): 用户id
            user_sign_in (SignIn): 签到数据
            user_prop (UserProperty): 用户数据

        Returns:
            Tuple[str, Optional[Dict[str, Any]]]: str为效果发生语句，第二个返回值若存在，则是下一次调用时的参数
        """
        if self.func is None:
            return "什么事都没发生"
        params_required = inspect.signature(self.func).parameters
        params = {}
        if "user_id" in params_required:
            params["user_id"] = user_id
        if "user_sign_in" in params_required:
            params["user_sign_in"] = user_sign_in
        if "user_prop" in params_required:
            params["user_prop"] = user_prop
        if iscoroutinefunction(self.func):
            return await self.func(**params)
        return self.func(**params)

    async def next_effect(
        self, user_id: int, user_sign_in: SignIn, user_prop: UserProperty, **kwargs
    ) -> Optional[Any]:
        """下一次签到时自动触发调用"""
        if self.next_func is None:
            return None
        params_required = inspect.signature(self.next_func).parameters
        params = {}
        if "user_id" in params_required:
            params["user_id"] = user_id
        if "user_sign_in" in params_required:
            params["user_sign_in"] = user_sign_in
        if "user_prop" in params_required:
            params["user_prop"] = user_prop
        if iscoroutinefunction(self.next_func):
            return await self.next_func(**params, **kwargs)  # type: ignore
        return self.next_func(**params, **kwargs)  # type: ignore

    def has_next_effect(self) -> bool:
        return self.next_func is not None


class SignInEffect:
    def __init__(self) -> None:
        self.__effects: List[Effect] = []
        self.__weights: List[int] = []
        self.__name_to_effect: Dict[str, Effect] = {}

    def __call__(self, name: str, weight: int = 1) -> Any:
        """添加一个签到随机效果

        Args:
            name (str): 唯一的效果名.
            weight (int): 效果的权重，越高则可能性越高，建议在1-10之间. Defaults to 1.

        Returns:
            Any: _description_
        """

        def add_effect(
            func: Callable[
                [int, SignIn, UserProperty],
                Union[
                    Union[str, Coroutine[Any, Any, str]],
                    Tuple[
                        Union[str, Coroutine[Any, Any, str]], Optional[Dict[str, Any]]
                    ],
                ],
            ]
        ):
            effect = Effect(name=name, func=func)
            self.__effects.append(effect)
            self.__name_to_effect[name] = effect
            self.__weights.append(weight)
            logger.info(f"已成功添加签到效果：{name}")

        return add_effect

    def next(self, name: str) -> Any:
        """为名字为name的效果添加一个下一次签到才会触发的效果
            函数前3个参数和签到效果一样，后面参数可自定义

        Args:
            name (str): 唯一的效果名.

        Returns:
            Any: _description_
        """

        def add_next_effect(func: Callable[..., Union[str, Coroutine[Any, Any, str]]]):
            if name not in self.__name_to_effect:
                raise Exception(f"名字为 {name} 的签到效果不存在")
            self.__name_to_effect[name].next_func = func

        return add_next_effect

    def random_effect(self) -> Effect:
        """获取一个随机效果

        Returns:
            Effect: _description_
        """
        return random.choices(self.__effects, weights=self.__weights)[0]

    def get_effect_by_name(self, name: str) -> Optional[Effect]:
        """由效果名获取效果

        Args:
            name (str): 效果名

        Returns:
            Optional[Effect]: 若不存在返回None
        """
        return self.__name_to_effect.get(name)


sign_in_effect = SignInEffect()
"""添加一个签到随机效果

Args:
    weight (int, optional): 效果的权重，越高则可能性越高，建议在1-10之间. Defaults to 1.
    desc (Optional[str], optional): 描述，仅供生成日志. Defaults to None.
"""
