import re

from nonebot import on_startswith
from nonebot.params import Startswith
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageEvent

from .data_source import get_data, search_jr

__plugin_meta__ = PluginMetadata(
    name="光之收藏家",
    description="光之收藏家幻化推荐",
    usage="""
usage：
    从光之收藏家获取一个幻化
    指令：
        /hh [职业] [种族] [性别] : 随机返回至少一个参数的幻化
    示例：
        /hh 占星
        /hh 拉拉菲尔 男
    可加参数 rank:[mode] : 随机返回一个职业或种族排行榜点赞最多的幻化(可用mode: hour, week, month, all)
    如：/hh 公肥 rank:month
    /hh [职业] [种族] [性别] item:物品名 : 查询指定装备至今点赞排行榜的幻化搭配，装备名必须全名且正确(无“rank”参数)
    如：/hh 公肥 item:巫骨低吟者短衣
    Powered by https://www.ffxivsc.cn
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "FF14"

hh = on_startswith("/hh", priority=5, block=True)


@hh.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    args = event.get_plaintext().removeprefix(cmd).strip()
    if not args:
        await hh.send("参数错误，请发送[/光之收藏家]查看帮助")
    time = 0
    sort = 0
    item_flag = False
    item_name = None
    if rank := re.search(r"rank:(hour|week|month|all)", args):
        sort = 1
        time = {"hour": "1", "week": "2", "month": "3", "all": "0"}.get(rank.group(1))
        args = args.replace(rank.group(0), "")
    if item := re.search(r"item:(\S+)", args):
        item_flag = True
        item_name = item.group(1)
        args = args.replace(item_name, "")
    jobs, races, sex = await get_data()
    job_id: int = 0
    race_id: int = 0
    sex_id: int = 0
    for job in jobs:
        if job in args:
            args = args.replace(job, "")
            job_id = jobs[job]
            break
    for race in races:
        if race in args:
            args = args.replace(race, "")
            race_id = races[race]
            break
    for s in sex:
        if s in args:
            args = args.replace(s, "")
            sex_id = sex[s]
            break
    img = await search_jr(
        job=job_id,
        race=race_id,
        sex=sex_id,
        sort=sort,
        time=time,
        item_name=item_name,
        item_flag=item_flag,
    )
    await hh.send(img)
