"""
https://github.com/Kyomotoi/ATRI/tree/main/ATRI/plugins/code_runner
"""

from random import choice

from nonebot import on_command
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg, ArgPlainText
from nonebot.adapters.onebot.v11.helpers import Cooldown
from nonebot.adapters.onebot.v11 import Message, unescape

from .data_source import runner, list_supp_lang

__plugin_meta__ = PluginMetadata(
    name="在线运行代码",
    description="使用https://glot.io/在线运行代码",
    usage=f"""
usage：
    在线运行代码，输出支持markdown语法
    指令：
        code> 语言 代码
    例子：
        code> cpp 
        #include<iostream> 
        int main() {{ std::cout << "hello migang" << std::endl; }}
支持的语言：
{list_supp_lang(7)}
""".strip(),
    extra={
        "unique_name": "migang_code_runner",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

_flmt_notice = choice(["稍微慢一点哦~", "不要这么着急！", "歇会歇会~~"])


code_runner = on_command("code>", priority=5, block=True)


@code_runner.handle([Cooldown(5, prompt=_flmt_notice)])
async def _(matcher: Matcher, args: Message = CommandArg()):
    msg = args.extract_plain_text()
    if msg:
        matcher.set_arg("opt", args)


@code_runner.got("opt", prompt="需要运行的语言及代码？\n获取帮助：/code.help")
async def _(opt: str = ArgPlainText("opt")):
    await code_runner.finish(await runner(unescape(opt)))
