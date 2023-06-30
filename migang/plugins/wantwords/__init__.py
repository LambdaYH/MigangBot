import asyncio
from typing import Annotated

import aiohttp
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message

__plugin_meta__ = PluginMetadata(
    name="反向找词",
    description="通过描述反向找词",
    usage="""
基于https://wantwords.net/
通过描述反向找词
指令：
    找词 模式（zhzh/enzh/zhen/enen） 描述
示例：
    找词 zhzh 表示飘在天上
说明：
    模式中的zh表示中文，en表示英文，zhen就表示使用中文描述找英文词，其他同理
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "一些工具"

wantwords = on_command("找词", aliases={"反向找词"}, priority=5, block=True)


api_url = "https://wantwords.net/{target_language}RD"

mode_to_params = {
    "zhzh": ("Chinese", "ZhZh"),
    "enzh": ("Chinese", "EnZh"),
    "zhen": ("English", "ZhEn"),
    "enen": ("English", "EnEn"),
}


@wantwords.handle()
async def _(args: Annotated[Message, CommandArg()]):
    args = args.extract_plain_text().split(" ", maxsplit=1)
    if len(args) != 2 or args[0].lower() not in mode_to_params:
        await wantwords.finish("格式错误，请按照【找词 模式（zhzh/enzh/zhen/enen） 描述】发送")
    mode = mode_to_params[args[0].lower()]
    description = args[1].strip()
    try:
        async with aiohttp.ClientSession() as client:
            r = await client.get(
                api_url.format(target_language=mode[0]),
                params={"q": description, "m": mode[1], "f": 1},
            )
            data = await r.json()
            ret = []
            # 返回5个
            idx_icon = ["①", "②", "③", "④", "⑤"]
            for idx, item in enumerate(data[:5]):
                ret.append(f"{idx_icon[idx]} {item['w']}：{item['d']}")
            await wantwords.send("\n".join(ret))
    except asyncio.TimeoutError:
        await wantwords.send("出错了...")
