import re
from typing import Any, Set, Dict, List, Callable, get_type_hints

import cattrs
from nonebot.log import logger
from nonebot.utils import is_coroutine_callable


# 扩展插件基类
class Extension:
    def __init__(
        self, func: Callable, name: str, description: str, refer_word: List[str]
    ):
        self.__func: Callable = func
        self.__name: str = name
        self.__description: str = description
        self.__refer_word: List[str] = refer_word

        params = get_type_hints(self.__func)
        self.__params = {}
        for k, v in params.items():
            if k in ("bot_name", "user_send_raw_text", "bot_send_raw_text", "return"):
                continue
            if match := re.match(r"<class '(\S+)'>", str(v)):
                self.__params[k] = match.group(1)
            elif str(v).startswith("typing."):
                self.__params[k] = str(v).removeprefix("typing.")

    @property
    def parameter(self) -> Set[str]:
        return self.__params.keys()

    async def run(self, arg_dict) -> dict:
        """调用扩展"""
        args = get_type_hints(self.__func)
        if "return" in args:
            args.pop("return")
        params = {}
        for k in args:
            if k in arg_dict:
                params[k] = cattrs.structure(arg_dict[k], args[k])
        if len(params) != len(args):
            return {}
        return (
            (await self.__func(**params))
            if is_coroutine_callable(self.__func)
            else self.__func(**params)
        )

    def generate_description(self, chat_history_text="") -> str:
        """生成扩展描述prompt(供bot参考用)"""
        # print(chat_history_text)
        # 判断参考词
        if self.__refer_word and chat_history_text:
            for refer_word in self.__refer_word:
                if refer_word in chat_history_text:
                    break
            else:
                return ""
        args_desc: str = "; ".join([f"{k}:{v}" for k, v in self.__params.items()])
        args_desc = "no args" if args_desc == "" else args_desc
        return f"- {self.__name}: {args_desc} ({self.__description})\n"


class ExtensionManager:
    # 管理拓展
    def __init__(self) -> None:
        self.__extensions: Dict[str, Extension] = {}

    def __call__(self, name: str, description: str, refer_word: List[str]) -> Any:
        def __add_extension(func: Callable):
            self.__extensions[name] = Extension(
                func=func, name=name, description=description, refer_word=refer_word
            )
            logger.info(f"chat_chatgpt已加载拓展 {name}")

        return __add_extension

    def get_extension(self, name: str) -> Extension:
        return self.__extensions.get(name)

    def get_desciption(self, chat_history: str) -> str:
        return "".join(
            [
                extention.generate_description(chat_history_text=chat_history)
                for extention in self.__extensions.values()
            ]
        )


extension_manager = ExtensionManager()
