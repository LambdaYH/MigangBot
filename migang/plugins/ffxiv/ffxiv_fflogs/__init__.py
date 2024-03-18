"""FFLogs

查询副本输出数据。
https://github.com/he0119/CoolQBot/tree/master/src/plugins/ff14/plugins/ff14_fflogs
"""
from typing import Literal, cast

from nonebot import get_driver
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot_plugin_datastore import get_plugin_data
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot_plugin_alconna import At, Args, Text, Alconna, MultiVar, on_alconna

from .api import fflogs
from . import migrations
from .utils import strtobool
from .data import FFLOGS_DATA
from .config import plugin_config

__plugin_meta__ = PluginMetadata(
    name="FFLogs",
    description="副本输出查询",
    usage="""更新副本数据
/dps update

查询输出排行榜：
/dps 副本名 职业 DPS种类（支持 rdps adps pdps，留空默认为 rdps）
查询指定角色的排名：
/dps 副本名 角色名 服务器名（拂晓之间, etc.）
也可直接查询自己绑定角色的排名：
/dps 副本名 me
或查询他人绑定的角色排名
/dps 副本名 @他人
查询当前QQ号绑定的角色
/dps me
绑定自己的角色
/dps me 角色名 服务器名
查询他人绑定的角色
/dps @他人""",
    type="application",
    supported_adapters={"~onebot.v11"},
    extra={"orm_version_location": migrations},
)

__plugin_category__ = "FF14"
__plugin_aliases__ = ["fflogs"]

plugin_data = get_plugin_data()
global_config = get_driver().config

fflogs_cmd = on_alconna(
    Alconna("/dps", Args["argv", MultiVar(At | str, flag="*")]),
    use_cmd_start=True,
)


@fflogs_cmd.handle()
async def fflogs_handle(bot: Bot, event: MessageEvent, argv: tuple[str | At, ...]):
    if not argv:
        await fflogs_cmd.finish(f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}")

    # 检查 Token 是否设置
    if not plugin_config.fflogs_token:
        await fflogs_cmd.finish("对不起，Token 未设置，无法查询数据。\n请先在 .env 中配置好 Token 后再尝试查询数据。")

    if argv[0] == "update" and len(argv) == 1:
        await FFLOGS_DATA.update()
        data = await FFLOGS_DATA.data
        await fflogs_cmd.finish(f"副本数据更新成功，当前版本为 {data.version}。")

    # 缓存相关设置
    if argv[0] == "cache":
        cache_boss = await plugin_data.config.get("cache_boss", [])
        if len(argv) == 2:
            if argv[1] == "list":
                if not cache_boss:
                    await fflogs_cmd.finish("当前没有缓存副本。")
                await fflogs_cmd.finish("当前缓存的副本有：\n" + "\n".join(cache_boss))
            # 检查是否是超级用户
            if not await SUPERUSER(bot=bot, event=event):
                await fflogs_cmd.finish("抱歉，你没有权限设置缓存。")
            if strtobool(str(argv[1])):
                if not fflogs.is_cache_enabled:
                    await fflogs.enable_cache()
                await fflogs_cmd.finish("已开始定时缓存。")
            else:
                if fflogs.is_cache_enabled:
                    await fflogs.disable_cache()
                await fflogs_cmd.finish("已停止定时缓存。")
        if len(argv) == 3:
            # 检查是否是超级用户
            if not await SUPERUSER(bot=bot, event=event):
                await fflogs_cmd.finish("抱歉，你没有权限设置缓存。")
            if argv[1] == "add":
                cache_boss.append(str(argv[2]))
                await plugin_data.config.set("cache_boss", cache_boss)
                await fflogs_cmd.finish(f"已添加副本 {argv[2]}。")
            elif argv[1] == "del":
                if argv[2] in cache_boss:
                    cache_boss.remove(argv[2])
                    await plugin_data.config.set("cache_boss", cache_boss)
                    await fflogs_cmd.finish(f"已删除副本 {argv[2]}。")
                else:
                    await fflogs_cmd.finish(f"没有缓存 {argv[2]}，无法删除。")
        else:
            if fflogs.is_cache_enabled:
                await fflogs_cmd.finish("定时缓存开启中")
            else:
                await fflogs_cmd.finish("定时缓存关闭中")

    if argv[0] == "me" and len(argv) == 1:
        character = await fflogs.get_character(event.get_user_id())
        if not character:
            await fflogs_cmd.finish(
                At(flag="user", target=event.get_user_id())
                + Text("抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me 角色名 服务器名\n绑定自己的角色。")
            )

        await fflogs_cmd.finish(
            At(flag="user", target=event.get_user_id())
            + Text(
                f"你当前绑定的角色：\n角色：{character.character_name}\n服务器：{character.server_name}"
            )
        )

    if isinstance(argv[0], At) and len(argv) == 1:
        character = await fflogs.get_character(argv[0].target)
        if not character:
            await fflogs_cmd.finish(
                At(flag="user", target=event.get_user_id())
                + Text("抱歉，该用户没有绑定最终幻想14的角色。")
            )

        await fflogs_cmd.finish(
            argv[0]
            + Text(
                f"当前绑定的角色：\n角色：{character.character_name}\n服务器：{character.server_name}"
            )
        )

    if argv[0] == "me" and len(argv) == 3:
        await fflogs.set_character(event.get_user_id(), str(argv[1]), str(argv[2]))
        await fflogs_cmd.finish(
            At(flag="user", target=event.get_user_id()) + Text("角色绑定成功！")
        )

    if argv[0] == "classes" and len(argv) == 1:
        data = await fflogs.classes()
        await fflogs_cmd.finish(str(data))

    if argv[0] == "zones" and len(argv) == 2:
        data = await fflogs.zones()
        zones = next(filter(lambda x: str(x.id) == argv[1], data))
        await fflogs_cmd.finish(str(zones))

    # 判断查询排行是指个人还是特定职业
    if len(argv) == 2:
        # <BOSS名> me
        # <BOSS名> <@他人>
        # <BOSS名> <职业名>
        if isinstance(argv[0], str) and isinstance(argv[1], At):
            # @他人的格式
            data = await get_character_dps_by_user_id(argv[0], argv[1].target)
        elif (
            isinstance(argv[0], str)
            and isinstance(argv[1], str)
            and argv[1].lower() == "me"
        ):
            data = await get_character_dps_by_user_id(argv[0], event.get_user_id())
        else:
            data = await fflogs.dps(*argv)  # type:ignore
        await fflogs_cmd.finish(data)

    if len(argv) == 3:
        # <BOSS名> <职业名> <DPS种类>
        # <BOSS名> <角色名> <服务器名>
        args = cast(tuple[str, str, str], argv)
        dps_type = args[2].lower()
        if dps_type in ["adps", "rdps", "pdps", "ndps"]:
            dps_type = cast(Literal["adps", "rdps", "pdps", "ndps"], dps_type)
            data = await fflogs.dps(args[0], args[1], dps_type)
        else:
            data = await fflogs.character_dps(args[0], args[1], args[2])
        await fflogs_cmd.finish(data)

    await fflogs_cmd.finish(f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}")


async def get_character_dps_by_user_id(boss_nickname: str, uid: str):
    """通过 BOSS 名称和 QQ 号来获取角色的 DPS 数据"""
    user = await fflogs.get_character(uid)
    if not user:
        return "抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me <角色名> <服务器名>\n绑定自己的角色。"
    return await fflogs.character_dps(
        boss_nickname, user.character_name, user.server_name
    )
