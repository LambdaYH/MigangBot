import re

from nonebot import on_message
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11 import ActionFailed, GroupMessageEvent

from migang.core import TaskItem

from .utils import parser_manager
from . import weibo, github, bilibili  # noqa

__plugin_meta__ = PluginMetadata(
    name="群内链接解析",
    description="解析群聊消息中的各类链接",
    usage="""
usage：
    检测群内各类链接后自动解析
    目前支持：
        B站
        微博
        Github
""".strip(),
    extra={
        "unique_name": "migang_url_parse",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

BILIBILI_TASK = "url_parse_bilibili"
GITHUB_TASK = "url_parse_github_repo_card"
WEIBO_TASK = "url_parse_weibo_parse"


__plugin_hidden__ = True
__plugin_task__ = (
    TaskItem(task_name=BILIBILI_TASK, name="B站链接解析", default_status=True),
    TaskItem(task_name=GITHUB_TASK, name="github链接解析", default_status=True),
    TaskItem(task_name=WEIBO_TASK, name="微博链接解析", default_status=True),
)

URL_PATTERN = re.compile(
    r"https?:[/|\\](?:[a-zA-Z]|[0-9]|[$-_@.&#+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)
BVID_AID_PATTERN = re.compile(r"((?:av|AV)\d+|(?:BV|bv)[a-zA-Z0-9]{10})")


async def _rule(event: GroupMessageEvent, state: T_State) -> bool:
    msg = str(event.message)
    if msg.startswith("【FF14/时尚品鉴】"):
        return False
    url_set = set(URL_PATTERN.findall(msg))
    # 对bv,av号额外处理
    if not url_set:
        for id_ in BVID_AID_PATTERN.findall(msg):
            url_set.add(f"https://www.bilibili.com/video/{id_}")
    if url_set:
        if parsers := await parser_manager.get_parser(
            urls=url_set, group_id=event.group_id
        ):
            state["parses"] = parsers
            return True
    return False


url_parse = on_message(permission=GROUP, priority=22, block=True, rule=_rule)


@url_parse.handle()
async def _(event: GroupMessageEvent, state: T_State):
    msgs = await parser_manager.do_parse(state["parses"])
    for msg in msgs:
        if msg is not None:
            try:
                await url_parse.send(msg)
            except ActionFailed:
                logger.warning(f"群 {event.group_id} 发送解析消息失败")
