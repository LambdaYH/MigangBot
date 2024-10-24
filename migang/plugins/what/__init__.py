"""移植自meetwq/mybot，视网络环境可能有几个源不可用
"""
import re

from nonebot.plugin import PluginMetadata
from nonebot import on_command, on_keyword
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg, EventPlainText

from migang.core import ConfigItem

from .data_source import get_content

__plugin_meta__ = PluginMetadata(
    name="聚合百科",
    description="聚合百科，尝试找到你想知道的",
    usage="""
usage：
    聚合多个源的百科，视网络环境搜索可能不稳定
    当前搜索源包含：
        - 萌娘百科
        - nbnhhsh
        - 最终幻想14Wiki（獭獭那抄的）
    指令：
        百科 xxx
        xxx是什么/是谁/是啥
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "一些工具"
__plugin_config__ = ConfigItem(
    key="baidubaike_key", description="从 https://api.a20safe.com/post/3 获取"
)


commands = {"是啥", "是什么", "是谁"}
what = on_keyword(commands, priority=14)
baike = on_command("百科", block=True, priority=13)


@what.handle()
async def _(msg: str = EventPlainText()):
    def split_command(msg):
        for command in commands:
            if command in msg:
                prefix_suffix = re.split(command, msg)
                if len(prefix_suffix) == 2:
                    return prefix_suffix[0], prefix_suffix[1]
        return "", ""

    msg = msg.strip().strip(".>,?!。，（）()[]【】")
    prefix_words = ["这", "这个", "那", "那个", "你", "我", "他", "它"]
    suffix_words = ["意思", "梗", "玩意", "鬼"]
    prefix, suffix = split_command(msg)
    if (not prefix or prefix in prefix_words) or (
        suffix and suffix not in suffix_words
    ):
        what.block = False
        await what.finish()
    keyword = prefix

    res = await get_content(keyword)

    if res:
        what.block = True
        await what.finish(res)
    else:
        what.block = False
        await what.finish()


@baike.handle()
async def _(msg: Message = CommandArg()):
    keyword = msg.extract_plain_text()
    if not keyword:
        await baike.finish()

    res = await get_content(keyword)
    if res:
        await baike.finish(res)
    else:
        await baike.finish("找不到相关的条目")
