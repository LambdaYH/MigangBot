from nonebot import on_command, require
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    Message,
    GroupMessageEvent,
    MessageEvent,
)

from .data_source import (
    get_server_info,
    server_status,
    add_server,
    del_server,
    get_server_list,
    get_add_info,
)

require("nonebot_plugin_imageutils")

__plugin_meta__ = PluginMetadata(
    name="MC服务器状态查询",
    description="查询MC服务器状态",
    usage="""
usage：
    指令：
        添加mcs 服务器名 ip:<port> je/be
        查询mcs 服务器名
        删除mcs 服务器名
        mcslist/mc服务器列表                   ：

        查询mcs ip:<port> je/be

    说明：
        je对应Java版，be对应基岩版

        【添加/删除mcs】 可管理本群（用户）数据库中以 服务器名 为自定义别名的服务器，方便快捷查看信息并使用 【查询mcs 服务器名】查询状态
        发送 【mcslist】 可查看本群（用户）数据库中保存的服务器信息

        若服务器未加入数据库，可使用【查询mcs ip:<port> je/be】指令查询以 ip:<port> 为地址的服务器状态，当仅有ip时，将使用默认端口

    例子：
        添加mcs hypixel mc.hypixel.net je
        添加mcs 假的服务器 example.mc.com:1206 be

        查询mcs hypixel
        查询mcs mc.hypixel.net je
        查询mcs example.mc.com:1206 be

        删除mcs hypixel
""".strip(),
    extra={
        "unique_name": "MCServerStatusQuery",
        "example": "添加mcs hypixel mc.hypixel.net je\n添加mcs 假的服务器 example.mc.com:1206 be\n查询mcs hypixel\n查询mcs mc.hypixel.net je\n查询mcs example.mc.com:1206 be\n删除mcs hypixel",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "一些工具"

query = on_command("查询mcs", aliases={"qmcs"}, priority=5)
add_mc = on_command("添加mcs", aliases={"addmcs"}, priority=5)
del_mc = on_command("删除mcs", aliases={"delmcs"}, priority=5)
mc_list = on_command("mcslist", aliases={"mc服务器列表", "MC服务器列表"}, priority=5)


@query.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    params = args.extract_plain_text().strip().split(" ")
    host, port, sv_type = None, None, None
    if len(params) != 2:
        if len(params) != 1:
            await query.finish("查询参数错误，请按照[查询mcs ip:<port> je/be]重新发送")
        group_id, user_id = (
            event.group_id if isinstance(event, GroupMessageEvent) else None,
            event.user_id,
        )
        if host_port := await get_server_info(
            group_id=group_id, user_id=user_id, name=params[0]
        ):
            host, port, sv_type = host_port[0], host_port[1], host_port[2]
        else:
            await query.finish(
                f"名称为 {params[0]} 的服务器未添加，请添加后查询或发送[查询mcs ip:<port> je/be]查询"
            )
    if not host:
        host_port = params[0].split(":")
        host = host_port[0]
        if len(host_port) == 2:
            port = int(host_port[1])
        sv_type = params[1]
    await query.send(
        await server_status(
            host=host,
            port=port,
            sv_type=sv_type,
        )
    )


@add_mc.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    params = args.extract_plain_text().strip().split(" ")
    if len(params) != 3:
        await add_mc.finish(f"参数错误，请按照[添加mcs 服务器名 ip:<port> je/be]重新发送")
    group_id, user_id = (
        event.group_id if isinstance(event, GroupMessageEvent) else None,
        event.user_id,
    )
    if await add_server(
        group_id=group_id,
        user_id=user_id,
        name=params[0],
        host=params[1],
        sv_type=params[2],
    ):
        await add_mc.finish(
            get_add_info(name=params[0], host=params[1], sv_type=params[2])
        )
    await add_mc.send(f"名称为 {params[0]} 的MC服务器已存在，请更换服务器名")


@del_mc.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    name = args.extract_plain_text().strip()
    group_id, user_id = (
        event.group_id if isinstance(event, GroupMessageEvent) else None,
        event.user_id,
    )
    if await del_server(group_id=group_id, user_id=user_id, name=name):
        await del_mc.finish(f"MC服务器 {name} 已删除")
    await del_mc.send(f"名称为 {name} 的MC服务器不存在")


@mc_list.handle()
async def _(event: MessageEvent):
    group_id, user_id = (
        event.group_id if isinstance(event, GroupMessageEvent) else None,
        event.user_id,
    )
    await mc_list.send(await get_server_list(group_id=group_id, user_id=user_id))
