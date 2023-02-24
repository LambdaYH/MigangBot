from nonebot import on_command, on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import MessageEvent, Message, GroupMessageEvent, Bot

from .data_source import get_fabing, get_data

__plugin_meta__ = PluginMetadata(
    name="枝网小作文",
    description="生成发病小作文",
    usage="""
usage：
    生成发病小作文
    指令：
        [发病 对象]  对发病对象发病
        [发病小作文] 随机发送一篇发病小作文
""".strip(),
    extra={
        "unique_name": "migang_asoulcnki",
        "example": "发病\n发病小作文",
        "author": "migang",
        "version": 0.1,
    },
)

article = on_fullmatch("发病小作文", block=True, priority=13)
fabin = on_command("发病", block=True, priority=13)


@article.handle()
async def _():
    await article.finish(get_data()["text"])


@fabin.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    target = ""
    for seg in arg:
        if seg.type == "at":
            assert isinstance(event, GroupMessageEvent)
            info = await bot.get_group_member_info(
                group_id=event.group_id, user_id=seg.data["qq"]
            )
            target = info.get("card", "") or info.get("nickname", "")
            break
    if not target:
        target = arg.extract_plain_text().strip()
    if not target:
        await fabin.finish("请发送[发病 对象]~", at_sender=True)
    author = event.sender.card or event.sender.nickname
    await fabin.send(await get_fabing(target, author))
