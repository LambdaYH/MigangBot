from nonebot import on_startswith
from nonebot.params import Startswith
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment

from .data_source import (
    get_area_id,
    get_server_id,
    get_house_info,
    get_house_size_id,
    get_region_type_id,
)

__plugin_meta__ = PluginMetadata(
    name="房屋查询",
    description="ff14售楼中心",
    usage="""
usage：
    由https://house.ffxiv.cyou/提供
    空房查询（虽然网页版应该更好用
    指令：
        /house 服务器名 房子大小（s/m/l，可省略） 住宅区（海都/沙都/森都/白银/雪都，可省略） 房屋类型（个人/部队，可省略）
    示例：
        第一个参数必须是服务器名，后面的三个参数都是可选且顺序任意的
        /house 拂晓之间
        /house 拂晓之间 m 海都
        /house 拂晓之间 森都
        /house 拂晓之间 部队 森都 s
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "FF14"

house = on_startswith("/house", priority=5, block=True)


@house.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    args = event.get_plaintext().removeprefix(cmd).strip()
    if not args:
        await house.finish("参数错误，请发送[/房屋查询]查看帮助")
    args = args.split(" ")
    server_id = get_server_id(args[0])
    if not server_id:
        await house.finish("服务器是必须输入的哦~")
    area_id = -1
    house_size_id = -1
    region_type_id = -1
    for arg in args[1:]:
        if (area := get_area_id(arg)) is not None:
            area_id = area
        elif (size := get_house_size_id(arg)) is not None:
            house_size_id = size
        elif (region := get_region_type_id(arg)) is not None:
            region_type_id = region
    ret = await get_house_info(
        server_id=server_id,
        area=area_id,
        house_size=house_size_id,
        region=region_type_id,
    )
    if ret is None:
        await house.finish("似乎没有空房子了...")
    await house.send(MessageSegment.image(ret))
