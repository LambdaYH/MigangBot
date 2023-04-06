import base64
import asyncio
import traceback
from io import BytesIO
from pathlib import Path
from typing import List, Union, Optional

import anyio
import jinja2
import aiohttp
from PIL import Image
from sqlalchemy import select
from nonebot.log import logger
from PIL.Image import Image as IMG
from mcstatus import JavaServer, BedrockServer
from nonebot_plugin_htmlrender import get_new_page
from nonebot_plugin_datastore import create_session
from nonebot.adapters.onebot.v11 import MessageSegment

from .draw import draw_list
from .model import McServerGroup, McServerPrivate
from .picmcstat.draw import draw_java, draw_error, draw_bedrock


async def get_server(
    group_id: Optional[int], user_id: Optional[int], name: str
) -> Union[McServerGroup, McServerPrivate, None]:
    """
    获取以name命名的服务器
    """
    async with create_session() as session:
        if group_id:
            server: Optional[McServerGroup] = await session.scalar(
                statement=select(McServerGroup).where(
                    McServerGroup.group_id == group_id, McServerGroup.name == name
                )
            )
        else:
            server: Optional[McServerPrivate] = await session.scalar(
                statement=select(McServerPrivate).where(
                    McServerPrivate.user_id == user_id, McServerPrivate.name == name
                )
            )
        return server


async def add_server(
    group_id: Optional[int], user_id: Optional[int], name: str, host: str, sv_type: str
):
    if await get_server(group_id=group_id, user_id=user_id, name=name):
        return False
    host_port = host.split(":")
    port = None
    if len(host_port) == 2:
        host = host_port[0]
        port = int(host_port[1])
    async with create_session() as session:
        server: Union[McServerGroup, McServerPrivate]
        if group_id:
            server = McServerGroup(
                group_id=group_id, name=name, host=host, port=port, sv_type=sv_type
            )
        else:
            server = McServerPrivate(
                user_id=user_id, name=name, host=host, port=port, sv_type=sv_type
            )
        session.add(server)
        await session.commit()
    return True


async def del_server(group_id: Optional[int], user_id: Optional[int], name: str):
    if not await get_server(group_id=group_id, user_id=user_id, name=name):
        return False
    async with create_session() as session:
        if group_id:
            server: Optional[McServerGroup] = await session.scalar(
                statement=select(McServerGroup).where(
                    McServerGroup.group_id == group_id, McServerGroup.name == name
                )
            )
        else:
            server: Optional[McServerPrivate] = await session.scalar(
                statement=select(McServerPrivate).where(
                    McServerPrivate.user_id == user_id, McServerPrivate.name == name
                )
            )
        await session.delete(server)
        await session.commit()
    return True


async def get_server_info(group_id: int, user_id: int, name: str):
    if detail := await get_server(group_id=group_id, user_id=user_id, name=name):
        return (detail.host, detail.port, detail.sv_type)
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


async def get_server_list(group_id: int, user_id: int) -> MessageSegment:
    servers: List[Union[McServerGroup, McServerPrivate]]
    async with create_session() as session:
        if group_id:
            servers = await session.scalars(
                statement=select(McServerGroup).where(
                    McServerGroup.group_id == group_id
                )
            )
        else:
            servers = await session.scalars(
                statement=select(McServerPrivate).where(
                    McServerPrivate.user_id == user_id
                )
            )
    server_text_list = []
    for server in servers:
        server_text_list.append(
            f"§b{server.name}§7 "
            + ("Java版" if server.sv_type == "je" else "基岩版")
            + f"\n§f{server.host}"
            + (f":{server.port}" if server.port else "")
        )
    if not server_text_list:
        return MessageSegment.image(draw_list("空"))
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


async def get_mc_uuid(username: str) -> str:
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as client:
            resp = await client.get(url)
            result = await resp.json(content_type=None)
        if not result:
            return "none"
        return result.get("id", "none")
    except Exception as e:
        logger.warning(f"获取mc用户 {username} 的UUID失败：{e}")
        return ""


async def get_crafatar(type_: str, uuid: str) -> Optional[bytes]:
    path = ""
    if type_ == "avatar":
        path = "avatars"
    elif type_ == "head":
        path = "renders/head"
    elif type_ == "body":
        path = "renders/body"
    elif type_ == "skin":
        path = "skins"
    elif type_ == "cape":
        path = "capes"

    url = f"https://crafatar.com/{path}/{uuid}?overlay"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as client:
            resp = await client.get(url)
            result = await resp.read()
        return result
    except Exception as e:
        logger.warning(f"获取mcuuid {uuid} 的 {type_} 失败：{e}")
        return None


template_path = Path(__file__).parent / "res" / "template"
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_path), enable_async=True
)


async def load_file(name):
    async with await anyio.open_file(template_path / name, "r", encoding="utf-8") as f:
        return await f.read()


env.filters["load_file"] = load_file


async def get_mc_model(uuid: str) -> Optional[BytesIO]:
    skin_bytes = await get_crafatar("skin", uuid)
    cape_bytes = await get_crafatar("cape", uuid)
    if not skin_bytes:
        return None
    skin = f"data:image/png;base64,{base64.b64encode(skin_bytes).decode()}"
    cape = (
        f"data:image/png;base64,{base64.b64encode(cape_bytes).decode()}"
        if cape_bytes
        else ""
    )

    try:
        template = env.get_template("skin.html")
        html = await template.render_async(skin=skin, cape=cape)

        images: List[IMG] = []
        async with get_new_page(viewport={"width": 200, "height": 400}) as page:
            await page.set_content(html)
            await asyncio.sleep(0.1)
            for _ in range(60):
                image = await page.screenshot(full_page=True)
                images.append(Image.open(BytesIO(image)))

        output = BytesIO()
        images[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=0.05 * 1000,
            loop=0,
            disposal=2,
            optimize=False,
        )
        return output
    except:
        logger.warning(traceback.format_exc())
        return None
