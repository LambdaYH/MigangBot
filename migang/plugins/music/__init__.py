"""
https://github.com/pcrbot/music
"""
import asyncio
import datetime
from typing import Tuple

from nonebot import on_command
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
from nonebot.params import ArgStr, Command, CommandArg
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11 import (
    Message,
    ActionFailed,
    MessageSegment,
    GroupMessageEvent,
)

from .data_source import render_music_list
from .qq_music import search as search_qq_music
from .kugo_music import search as search_kugo_music
from .kuwo_music import search as search_kuwo_music
from .migu_music import search as search_migu_music
from .netease_music import search as search_netease_music

__plugin_meta__ = PluginMetadata(
    name="点歌",
    description="点歌~",
    usage="""
usage：
    在线点歌
    仅群聊可用
    指令：
        点歌 [歌名]
        搜网易云 [歌名]
        搜QQ音乐 [歌名]
        搜咪咕 [歌名]
        搜酷我 [歌名]
        搜酷狗 [歌名]
        来一首xxxx
""".strip(),
    extra={
        "unique_name": "migang_music",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)
__plugin_category__ = "群功能"

cool_down = datetime.timedelta(seconds=18)  # 冷却时间
expire = datetime.timedelta(minutes=2)
music_select = {}
last_check = {}

src_func = {
    "netease": search_netease_music,
    "qq": search_qq_music,
    "migu": search_migu_music,
    "kuwo": search_kuwo_music,
    "kugo": search_kugo_music,
}


music_handler = on_command(
    "点歌", aliases={"搜歌曲", "我想听"}, priority=5, block=True, permission=GROUP
)

music_specfic_source = on_command(
    "搜网易云",
    aliases={"搜QQ音乐", "搜咪咕", "搜酷我", "搜qq音乐", "搜酷狗"},
    priority=5,
    block=True,
    permission=GROUP,
)


def _music_select_rule(event: GroupMessageEvent) -> bool:
    return (event.get_session_id() in music_select) or (
        event.group_id in last_check
        and datetime.datetime.now() - last_check[event.group_id] < expire
    )


music_select_handler = on_command(
    "选择",
    aliases={"选歌"},
    priority=5,
    block=True,
    permission=GROUP,
    rule=_music_select_rule,
)
music_laiyishou = on_command(
    "来一首",
    aliases={"点一首", "来首", "点首", "/music"},
    priority=5,
    block=True,
    permission=GROUP,
)


@music_specfic_source.handle()
async def _(
    event: GroupMessageEvent,
    state: T_State,
    cmd: Tuple[str, ...] = Command(),
    arg: Message = CommandArg(),
):
    if event.user_id in last_check:
        intervals = datetime.datetime.now() - last_check[event.user_id]
        if intervals < cool_down:
            await music_handler.finish(
                f"暂时很忙哦，请{(cool_down - intervals).seconds}秒之后再点歌~"
            )
    if args := arg.extract_plain_text():
        state["music_name"] = args
    source = cmd[0].lstrip("搜")
    if source in ("网易云",):
        state["search_source"] = "netease"
    elif source in ("qq音乐", "QQ音乐"):
        state["search_source"] = "qq"
    elif source in ("咪咕",):
        state["search_source"] = "migu"
    elif source in ("酷我",):
        state["search_source"] = "kuwo"
    elif source in ("酷狗",):
        state["search_source"] = "kugo"


@music_handler.handle()
async def _(event: GroupMessageEvent, state: T_State, arg: Message = CommandArg()):
    if event.user_id in last_check:
        intervals = datetime.datetime.now() - last_check[event.user_id]
        if intervals < cool_down:
            await music_handler.finish(
                f"暂时很忙哦，请{(cool_down - intervals).seconds}秒之后再点歌~"
            )
    if args := arg.extract_plain_text():
        state["music_name"] = args


@music_select_handler.handle()
async def _(event: GroupMessageEvent, state: T_State, arg: Message = CommandArg()):
    if (
        (event.get_session_id() not in music_select)
        and (event.group_id in last_check)
        and (datetime.datetime.now() - last_check[event.group_id] < expire)
    ):
        await music_select_handler.finish("不可以替他人选歌哦", at_sender=True)
    if args := arg.extract_plain_text():
        state["music_id"] = args


@music_handler.got("music_name", prompt="你想听什么呀？")
async def _(event: GroupMessageEvent, music_name: str = ArgStr("music_name")):
    music_list = await search_music(music_name)
    if music_list:
        logger.info("成功获取到歌曲列表")
        key = event.get_session_id()
        music_select[key] = {}
        for idx, music in enumerate(music_list):
            music_select[key][idx] = music
        img = await render_music_list(music_list=music_list, multi_source=True)
        await music_handler.send(MessageSegment.image(img))
        last_check[event.user_id] = datetime.datetime.now()
        last_check[event.group_id] = datetime.datetime.now()
    else:
        await music_handler.send("什么也没有找到OxO")


@music_specfic_source.got("music_name", prompt="你想听什么呀？")
async def _(
    event: GroupMessageEvent,
    state: T_State,
    music_name: str = ArgStr("music_name"),
):
    music_list = await src_func[state["search_source"]](music_name, 5)
    if music_list:
        logger.info("成功获取到歌曲列表")
        key = event.get_session_id()
        music_select[key] = {}
        for idx, music in enumerate(music_list):
            music_select[key][idx] = music
        img = await render_music_list(music_list=music_list)
        await music_specfic_source.send(MessageSegment.image(img))
        last_check[event.user_id] = datetime.datetime.now()
        last_check[event.group_id] = datetime.datetime.now()
    else:
        await music_specfic_source.send("什么也没有找到OxO")


@music_select_handler.got("music_id", prompt="请发送你想听的歌的id哦~")
async def _(event: GroupMessageEvent, music_id: str = ArgStr("music_id")):
    key = event.get_session_id()
    music_dict = music_select[key]
    if not music_id.isdigit():
        await music_select_handler.reject("序号必须是正整数哦，请重新发送序号")
    music_idx = int(music_id) - 1
    if music_idx in music_dict:
        song = music_dict[music_idx]
        if song["type"] == "163":
            music = MessageSegment.music("163", song["id"])
        elif song["type"] == "qq":
            music = MessageSegment.music("qq", song["id"])
        elif song["type"] == "custom":
            music = MessageSegment(type="music", data=song)
        try:
            await music_select_handler.send(music)
        except ActionFailed:
            logger.warning("歌曲发送异常")
    else:
        await music_select_handler.reject(f"序号 {music_id} 不存在哦，请重新发送序号")
    del music_select[key]
    del last_check[event.group_id]


async def search_music(
    music_name, sources: Tuple[str, ...] = ("netease", "qq", "migu")
):
    tasks = [src_func[s](music_name) for s in sources]
    r = await asyncio.gather(*tasks, return_exceptions=True)
    result = []
    for music_list in r:
        if isinstance(music_list, list):
            result += music_list
        else:
            logger.warning(f"获取歌曲列表出现异常：{music_list}")
    return result


@music_laiyishou.handle()
async def _(arg: Message = CommandArg()):
    music_name = arg.extract_plain_text()
    if not music_name:
        return
    if m := await search_netease_music(music_name, 1):
        await music_laiyishou.finish(MessageSegment.music(m[0]["type"], m[0]["id"]))
    else:
        await music_laiyishou.finish("没有找到这首歌呢~")
