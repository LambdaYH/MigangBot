from pathlib import Path
from io import BytesIO
import base64
import asyncio
import traceback
from typing import Optional, List

import anyio
import aiohttp
import jinja2
from mcstatus import BedrockServer, JavaServer
from PIL.Image import Image as IMG
from PIL import Image
from nonebot_plugin_htmlrender import get_new_page
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment

from .model import ServerDB
from .draw import draw_bedrock, draw_java, draw_error, draw_list

data_path = Path() / "data" / "mcquery"
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
