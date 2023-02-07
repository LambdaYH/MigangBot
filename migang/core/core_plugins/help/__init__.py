"""获取帮助图片、插件帮助、群被动状态
"""

from pathlib import Path

from nonebot import on_command, require
from nonebot.params import CommandArg
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
    MessageSegment,
)
from nonebot.permission import SUPERUSER
import aiofiles

from .data_source import get_help_image, get_plugin_help, get_task_image
from .utils import GROUP_HELP_PATH, USER_HELP_PATH, GROUP_TASK_PATH

require("nonebot_plugin_htmlrender")
require("nonebot_plugin_imageutils")


simple_help = on_command("帮助", aliases={"功能"}, priority=1, block=True, rule=to_me())
task_help = on_command("群被动状态", priority=1, block=True, permission=GROUP)


@simple_help.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip()
    if not args:
        image_file: Path
        group_id, user_id = None, None
        if type(event) is GroupMessageEvent:
            group_id = event.group_id
            image_file = GROUP_HELP_PATH / f"{group_id}.png"
        elif type(event) is PrivateMessageEvent:
            user_id = event.user_id
            image_file = USER_HELP_PATH / f"{user_id }.png"
        if image_file.exists():
            await simple_help.finish(MessageSegment.image(image_file))
        img = await get_help_image(
            group_id=group_id,
            user_id=user_id,
            super=await SUPERUSER(bot, event),
        )
        await simple_help.send(MessageSegment.image(img))
        async with aiofiles.open(image_file, "wb") as f:
            await f.write(img)
    else:
        if help := get_plugin_help(args):
            await simple_help.send(help)
        else:
            await simple_help.send(f"没有该插件的帮助信息")


@task_help.handle()
async def _(event: GroupMessageEvent):
    image_file = GROUP_TASK_PATH / f"{event.group_id}.png"
    if image_file.exists():
        await task_help.finish(MessageSegment.image(image_file))
    img = await get_task_image(event.group_id)
    await task_help.send(MessageSegment.image(img))
    async with aiofiles.open(image_file, "wb") as f:
        await f.write(img)
