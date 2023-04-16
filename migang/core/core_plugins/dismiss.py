from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11 import Bot, Message, GroupMessageEvent

from migang.core import ConfigItem, get_config

__plugin_hidden__ = True
__plugin_always_on__ = True

__plugin_meta__ = PluginMetadata(
    name="自助退群_",
    description="自助退群",
    usage="""
usage：
    指令：
        .dismiss [bot QQ号后四位] 使bot退群
""".strip(),
    extra={
        "unique_name": "migang_dismiss",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)
__plugin_config__ = ConfigItem(
    key="leave_msg", initial_value="哼！走了", default_value="", description="退群前最后说的话（"
)


dismiss = on_command(".dismiss", permission=GROUP, priority=1, block=True)


@dismiss.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    target_id = arg.extract_plain_text()
    bot_id = bot.self_id
    if event.is_tome() or target_id == bot_id[-4:] or target_id == bot_id:
        await dismiss.send(await get_config("leave_msg"))
        await bot.set_group_leave(group_id=event.group_id)
        await bot.send_private_msg(
            user_id=int(list(bot.config.superusers)[0]),
            message=f"{list(bot.config.nickname)[0]}已由dismiss指令退出群({event.group_id})",
        )
