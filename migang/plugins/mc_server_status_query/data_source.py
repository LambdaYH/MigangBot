from pathlib import Path
from typing import Optional

from mcstatus import BedrockServer, JavaServer
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment

from .model import ServerDB
from .draw import draw_bedrock, draw_java, draw_error, draw_list

data_path = Path() / "data" / "mcssq"
db_file = data_path / "mcserver.db"

data_path.mkdir(exist_ok=True, parents=True)

mcserverdb = ServerDB(db_file)


async def add_server(group_id: int, user_id: int, name: str, host: str, sv_type: str):
    if await mcserverdb.get_server(group_id=group_id, user_id=user_id, name=name):
        return False
    host_port = host.split(":")
    port = None
    if len(host_port) == 2:
        host = host_port[0]
        port = int(host_port[1])
    await mcserverdb.add_server(
        group_id=group_id,
        user_id=user_id,
        name=name,
        host=host,
        port=port,
        sv_type=sv_type,
    )
    return True


async def del_server(group_id: int, user_id: int, name: str):
    if not await mcserverdb.get_server(group_id=group_id, user_id=user_id, name=name):
        return False
    await mcserverdb.del_server(group_id=group_id, user_id=user_id, name=name)
    return True


async def get_server_info(group_id: int, user_id: int, name: str):
    if detail := await mcserverdb.get_server(
        group_id=group_id, user_id=user_id, name=name
    ):
        return (
            detail[0],
            detail[1],
            detail[2],
        )
    return None


async def server_status(host: str, port: Optional[int], sv_type: str):
    try:
        if sv_type == "je":
            status = await JavaServer(host=host, port=port).async_status()
            return MessageSegment.image(draw_java(status))
        else:
            status = await BedrockServer(host=host, port=port).async_status()
            return MessageSegment.image(draw_bedrock(status))
    except Exception as e:
        logger.warning(f"MC服务器查询失败：\nhost：{host}\nport：{port}\n类型：{sv_type}")
        return MessageSegment.image(draw_error(e=e, sv_type=sv_type))


async def get_server_list(group_id: int, user_id: int):
    servers = await mcserverdb.get_server_list(group_id=group_id, user_id=user_id)
    if not servers:
        return MessageSegment.image(draw_list("空"))
    server_text_list = []
    for server in servers:
        server_text_list.append(
            f"§b{server[0]}§7 "
            + ("Java版" if server[3] == "je" else "基岩版")
            + f"\n§f{server[1]}"
            + (f":{server[2]}" if server[2] else "")
        )
    return MessageSegment.image(draw_list("\n".join(server_text_list)))


def get_add_info(name: str, host: str, sv_type: str):
    return MessageSegment.image(
        draw_list(
            f"""
        §bMC服务器添加成功
        §7名称: §f{name}
        §7地址: §f{host}
        §7类型: §f{"Java版" if sv_type == "je" else "基岩版"}
        §6可发送 查询mcs {name} 查询服务器状态
    """.strip()
        )
    )
