from typing import List, get_type_hints

import cattrs

from migang.core.manager import goods_manager
from migang.core.models import GoodsInfo, GoodsGroup

goods_info_fields = GoodsInfo._meta.fields
if "name" in goods_info_fields:
    goods_info_fields.remove("name")


async def adjust_goods(name: str, args: str) -> None:
    args = args.strip().split(" ")
    goods = goods_manager.get_goods(name=name)
    type_hints = get_type_hints(GoodsInfo)
    for arg in args:
        kwargs = {}
        key, value = arg.split(":")
        if key in goods_info_fields:
            # 0：替换，1：增加，2：减少
            mode = 0
            if key[-1] in ("+", "-"):
                key = key[:-1]
                if key[-1] == "+":
                    mode = 1
                else:
                    mode = 2
            if key == "group":
                value = value.replace("，", ",").split(",")
            else:
                value = cattrs.structure(value, type_hints[key])
            if mode == 0:
                kwargs[key] = value
            else:
                if mode == 1:
                    if isinstance(value, List):
                        kwargs[key] = list(set(value) | set(goods.__dict__[key]))
                    else:
                        kwargs[key] = value + goods.__dict__[key]
                else:
                    if isinstance(value, List):
                        kwargs[key] = list(set(goods.__dict__[key]) - set(value))
                    elif isinstance(value, str):
                        continue
                    else:
                        kwargs[key] = goods.__dict__[key] - value
        await goods_manager.adjust(name, **kwargs)


goods_group_fields = GoodsGroup._meta.fields
if "name" in goods_group_fields:
    goods_group_fields.remove("name")


async def adjust_goods_group(name: str, args: str) -> None:
    args = args.strip().split(" ")
    goods_group = goods_manager.get_goods_group(name)
    type_hints = get_type_hints(GoodsInfo)
    for arg in args:
        kwargs = {}
        key, value = arg.split(":")
        if key in goods_group_fields:
            # 0：替换，1：增加，2：减少
            mode = 0
            if key[-1] in ("+", "-"):
                key = key[:-1]
                if key[-1] == "+":
                    mode = 1
                else:
                    mode = 2
            if key == "group":
                value = value.replace("，", ",").split(",")
            else:
                value = cattrs.structure(value, type_hints[key])
            if mode == 0:
                kwargs[key] = value
            else:
                if mode == 1:
                    if isinstance(value, List):
                        kwargs[key] = list(set(value) | set(goods_group.__dict__[key]))
                    else:
                        kwargs[key] = value + goods_group.__dict__[key]
                else:
                    if isinstance(value, List):
                        kwargs[key] = list(set(goods_group.__dict__[key]) - set(value))
                    elif isinstance(value, str):
                        continue
                    else:
                        kwargs[key] = goods_group.__dict__[key] - value
        await goods_manager.adjust_group(name, **kwargs)
