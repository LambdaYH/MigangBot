"""
https://github.com/iamwyh2019/aircon
"""
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot import require, on_command, on_fullmatch

require("nonebot_plugin_datastore")
from nonebot_plugin_datastore import get_session
from sqlalchemy.ext.asyncio.session import AsyncSession
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import Depends, Fullmatch, CommandArg
from nonebot.adapters.onebot.v11 import Bot, Message, GroupMessageEvent

from .airconutils import get_aircon, print_aircon, update_aircon, install_aircon

__plugin_meta__ = PluginMetadata(
    name="群空调",
    description="一个即使是看起来也没有用的群空调",
    usage="""
usage：
    一个即使是看起来也没有用的群空调
    指令:
        [开空调/关空调] 开/关空调
        [当前温度] 查看当前温度
        [设置温度/设置环境温度 <温度>] 设置温度或环境温度
        [设置风速 <档位(1/2/3)>] 设置风速
        [空调类型] 查看空调类型
        [升级空调/降级空调] 调整空调类型
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "群功能"

switch_aircon = on_fullmatch(("开空调", "关空调"), priority=5, block=True, permission=GROUP)
cur_temp = on_fullmatch("当前温度", priority=5, block=True, permission=GROUP)
set_temp = on_command("设置温度", priority=5, block=True, permission=GROUP)
set_env_temp = on_command("设置环境温度", priority=5, block=True, permission=GROUP)
set_wind_rate = on_command("设置风速", priority=5, block=True, permission=GROUP)
aircon_type = on_fullmatch("空调类型", priority=5, block=True, permission=GROUP)
switch_type = on_fullmatch(("升级空调", "降级空调"), priority=5, block=True, permission=GROUP)

ac_type_text = ["家用空调", "中央空调"]
AIRCON_HOME = 0
AIRCON_CENTRAL = 1


async def check_status(
    session: AsyncSession, group_id: int, matcher: Matcher, need_on: bool = True
):
    aircon = await get_aircon(session=session, group_id=group_id)
    if not aircon:
        await matcher.finish("空调还没装哦~发送“开空调”安装空调")

    if need_on and not aircon.is_on:
        await matcher.finish("💤你空调没开！")

    return aircon


async def check_range(
    matcher: Matcher, msg: str, low: int, high: int, errormsg, special=None
):
    try:
        if special is not None and msg in special:
            return special[msg]
        val = int(msg)
    except ValueError:
        await matcher.finish(f"⚠️输入有误！只能输入{low}至{high}的整数")

    if not low <= val <= high:
        await matcher.finish(errormsg)

    return val


@switch_aircon.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    cmd: str = Fullmatch(),
    session: AsyncSession = Depends(get_session),
):
    group_id = event.group_id
    if cmd[0] == "开":
        aircon = await get_aircon(session=session, group_id=group_id)
        if not aircon:
            ginfo = await bot.get_group_info(group_id=group_id)
            gcount = ginfo["member_count"]
            aircon = install_aircon(
                session=session, group_id=group_id, num_member=gcount
            )
            await switch_aircon.send(
                f"❄空调已安装~,发送[{list(bot.config.nickname)[0]}帮助群空调]查看使用说明~"
            )
        elif aircon.is_on:
            await switch_aircon.finish(
                f"❄空调开着呢！发送[{list(bot.config.nickname)[0]}帮助群空调]查看使用说明~"
            )
        update_aircon(aircon=aircon, ison=True)
        await switch_aircon.send("❄哔~空调已开\n" + print_aircon(aircon))
    else:
        aircon = await check_status(
            session=session, group_id=group_id, matcher=switch_aircon
        )
        update_aircon(aircon=aircon, ison=False)
        await switch_aircon.send("💤哔~空调已关\n" + print_aircon(aircon))
    await session.commit()


@cur_temp.handle()
async def _(
    event: GroupMessageEvent,
    session: AsyncSession = Depends(get_session),
):
    aircon = await check_status(
        session=session, group_id=event.group_id, matcher=cur_temp, need_on=False
    )
    update_aircon(aircon=aircon)
    msg = ("❄" if aircon.is_on else "💤空调未开启\n") + print_aircon(aircon)
    await cur_temp.send(msg)
    await session.commit()


@set_temp.handle()
async def _(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
):
    group_id = event.group_id
    aircon = await check_status(session=session, group_id=group_id, matcher=set_temp)
    temp = await check_range(
        set_temp, arg.extract_plain_text(), -273, 999999, "只能设置-273-999999°C喔"
    )
    if temp == 114514:
        await set_temp.finish("这么臭的空调有什么装的必要吗")
    update_aircon(aircon=aircon, settemp=temp)
    await set_temp.send("❄" + print_aircon(aircon))
    await session.commit()


@set_wind_rate.handle()
async def _(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
):
    group_id = event.group_id
    aircon = await check_status(
        session=session, group_id=group_id, matcher=set_wind_rate
    )
    if aircon.ac_type != AIRCON_HOME:
        await set_wind_rate.finish("只有家用空调能调风量哦！")

    wind_rate = await check_range(
        set_wind_rate,
        arg.extract_plain_text(),
        1,
        3,
        "只能设置1/2/3档喔",
        {"低": 1, "中": 2, "高": 3},
    )
    if not wind_rate:
        return
    update_aircon(aircon=aircon, windrate=wind_rate - 1)
    msg = print_aircon(aircon)
    await set_wind_rate.send("❄" + msg)
    await session.commit()


@set_env_temp.handle()
async def _(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
):
    aircon = await check_status(
        session=session, group_id=event.group_id, matcher=set_env_temp, need_on=False
    )
    env_temp = await check_range(
        set_env_temp,
        arg.extract_plain_text(),
        -273,
        999999,
        "只能设置-273-999999°C喔",
    )
    if env_temp == 114514:
        await set_env_temp.finish("这么臭的空调有什么装的必要吗")
    update_aircon(aircon=aircon, envtemp=env_temp)
    msg = ("❄" if aircon.is_on else "💤空调未开启\n") + print_aircon(aircon)

    await set_env_temp.send(msg)
    await session.commit()


@aircon_type.handle()
async def _(
    event: GroupMessageEvent,
    session: AsyncSession = Depends(get_session),
):
    aircon = await check_status(
        session=session, group_id=event.group_id, matcher=aircon_type, need_on=False
    )

    await aircon_type.send(f"当前安装了{ac_type_text[aircon.ac_type]}哦~")


@switch_type.handle()
async def _(
    event: GroupMessageEvent,
    cmd: str = Fullmatch(),
    session: AsyncSession = Depends(get_session),
):
    aircon = await check_status(
        session=session, group_id=event.group_id, matcher=switch_type, need_on=False
    )
    ac_type = aircon.ac_type
    if cmd[:2] == "升级":
        if ac_type == len(ac_type_text) - 1:
            await switch_type.finish("已经是最高级的空调啦！")
        update_aircon(aircon=aircon, actype=ac_type + 1)
        await switch_type.send(
            f"❄已升级至{ac_type_text[aircon.ac_type]}~\n" + print_aircon(aircon)
        )
    else:
        if ac_type == 0:
            await switch_type.finish("已经是最基础级别的空调啦！")
        update_aircon(aircon=aircon, actype=ac_type - 1)
        await switch_type.send(
            f"❄已降级至{ac_type_text[aircon.ac_type]}~\n" + print_aircon(aircon)
        )
    await session.commit()
