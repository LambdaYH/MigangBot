import random

from nonebot import on_message
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Message,
    MessageSegment,
    GroupMessageEvent,
)

from migang.utils.text import filt_message
from migang.core.exception import ConfigNoExistError
from migang.utils.tts import get_azure_tts, azure_tts_status
from migang.core import TaskItem, ConfigItem, check_task, sync_get_config

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="复读_",
    description="群友的本质是（）",
    usage="""
usage：
    几率性复读
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "群功能"
__plugin_config__ = ConfigItem(
    key="probability",
    initial_value=1.35,
    default_value=1.35,
    description="a的值，复读概率计算式：p_n = 1 - 1/a^n 递推式：p_n+1 = 1 - (1 - p_n) / a",
)
__plugin_task__ = TaskItem(task_name="repeat", name="复读", default_status=True)


class Fudu:
    def __init__(self):
        self.__data = {}

    def reset(self, key, content):
        self.__data[key]["data"] = content
        self.__data[key]["repeated"] = False
        self.__data[key]["prob"] = 0

    def prob(self, key) -> float:
        return self.__data[key]["prob"]

    def set_prob(self, key, p):
        self.__data[key]["prob"] = p

    def check(self, key, content) -> bool:
        self.__create(key)
        return self.__data[key]["data"] == content

    def is_repeated(self, key):
        return self.__data[key]["repeated"]

    def set_repeated(self, key):
        self.__data[key]["repeated"] = True

    def __create(self, key):
        if self.__data.get(key) is None:
            self.__data[key] = {"repeated": False, "data": None, "prob": 0}


_fudu_list = Fudu()

try:
    PROB_A = sync_get_config("probability")
except ConfigNoExistError:
    PROB_A = 1.35


def _rule(event: GroupMessageEvent) -> bool:
    if (not check_task(group_id=event.group_id, task_name="repeat")) or event.is_tome():
        return False
    add_msg = uniform_message(event.message)
    if not add_msg:
        return False
    if not _fudu_list.check(event.group_id, add_msg):
        _fudu_list.reset(event.group_id, add_msg)
        return False
    if not _fudu_list.is_repeated(event.group_id):
        p = _fudu_list.prob(event.group_id)
        if random.random() < p:
            return True
        else:
            _fudu_list.set_prob(event.group_id, 1 - (1 - p) / PROB_A)
    return False


repeat = on_message(
    permission=GROUP,
    priority=999,
    block=False,
    rule=_rule,
)


@repeat.handle()
async def _(event: GroupMessageEvent):
    plain_text = event.get_plaintext()
    _fudu_list.set_repeated(event.group_id)
    if random.random() < 0.10:
        if plain_text.endswith("打断施法！"):
            await repeat.finish("打断" + plain_text)
        else:
            await repeat.finish("打断施法！")
    if azure_tts_status() and random.random() < 0.20 and 0 < len(plain_text) < 50:
        await repeat.finish(
            MessageSegment.record(await get_azure_tts(filt_message(plain_text)))
        )
    else:
        await repeat.finish(filt_message(event.message))


def uniform_message(msg: Message) -> Message:
    msg_ret = ""
    for seg in msg:
        if seg.type == "text":
            msg_ret += seg.data["text"]
        elif seg.type == "image":
            msg_ret += seg.data["file"]
        else:
            return None
    return msg_ret
