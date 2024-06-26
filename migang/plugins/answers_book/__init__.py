"""
https://github.com/A-kirami/answersbook
"""
import random
import hashlib
import secrets
from pathlib import Path
from datetime import date

import anyio
import ujson as json
from aiocache import cached
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageEvent

__plugin_meta__ = PluginMetadata(
    name="答案之书",
    description="生成发病小作文",
    usage="""
usage：
    愿一切无解都有解！解除你的迷惑，终结你的纠结！
    （乱答.jpg）
    指令:
        翻看答案 + 问题
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "好玩的"

answers_book = on_command("翻看答案", priority=5, block=True)

path = Path(__file__).parent / "answersbook.json"


@cached(ttl=600)
async def get_data():
    async with await anyio.open_file(path, "r", encoding="utf-8") as f:
        return json.loads(await f.read())


async def get_answers(qid: int, question: str):
    words = await get_data()
    keys = list(words.keys())
    qid = float(qid)
    today = date.today()
    formatted_today = int(today.strftime("%y%m%d"))
    strnum = (
        f"{formatted_today * (qid +(secrets.randbelow(1001)/10000 - 0.05))}_{question}"
    )
    md5 = hashlib.md5()
    md5.update(strnum.encode("utf-8"))
    res = md5.hexdigest()
    random.seed(res)
    key = random.choice(keys)
    return words[key]["answer"]


@answers_book.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text()
    if not msg:
        await answers_book.finish("你想问什么问题呢？请重新发送[翻看答案+问题]", at_sender=True)
    await answers_book.send(await get_answers(event.user_id, msg), at_sender=True)
