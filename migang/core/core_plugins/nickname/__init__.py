"""设定与获取个人昵称
"""

from random import choice, randint

from nonebot.rule import to_me
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot import on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent

from migang.core.models import NickName
from migang.core import ConfigItem, get_config

__plugin_meta__ = PluginMetadata(
    name="昵称系统",
    description="昵称系统，在Bot眼中，你的昵称会被替换为昵称系统中所设定",
    usage="""
usage：
    个人昵称，各群以及私聊均通用
    所有指令都需要@
    指令：
        设定昵称：以后叫我 xxx
        查询昵称：我叫什么
        删除昵称：取消昵称
""".strip(),
    extra={
        "unique_name": "migang_nickname",
        "example": "以后叫我 xxx\n我叫什么\n删除昵称",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_always_on__ = True
__plugin_category__ = "基础功能"
__plugin_config__ = ConfigItem(
    key="black_words",
    initial_value=["爸", "爹", "爷", "父亲"],
    default_value=[],
    description="昵称系统的屏蔽词，包含屏蔽词的昵称无法被设定",
)

set_nickname = on_command(
    "以后叫我",
    aliases={"以后请叫我", "称呼我", "以后请称呼我", "以后称呼我", "叫我", "请叫我"},
    priority=1,
    block=True,
    rule=to_me(),
)
query_nickname = on_fullmatch(
    ("我叫什么", "我是谁", "我的名字"), priority=1, block=True, rule=to_me()
)
cancel_nickname = on_fullmatch("取消昵称", priority=5, block=True, rule=to_me())


@set_nickname.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    name = args.extract_plain_text().strip()
    if not name:
        await set_nickname.finish("....叫你...什么？", at_sender=True)
    if name in bot.config.nickname:
        await set_nickname.finish("我的名字可不能让你占用了！", at_sender=True)
    for word in await get_config("black_words"):
        if word in name:
            await set_nickname.finish("昵称中包含屏蔽词哦~请重新起一个", at_sender=True)
    bot_nickname = list(bot.config.nickname)[0]
    if len(name) > 10:
        name = list(name)

        s = set()
        for i in range(
            randint(1 + (int(len(name) / 10) * 2), 6 + (int(len(name) / 10) * 2))
        ):
            while (idx := randint(0, len(name) - 1)) not in s:
                name[idx] = "*"
                s.add(idx)
        ret = ""
        for i, ch in enumerate(name):
            if ch == "*":
                if i == 0 or name[i - 1] != "*":
                    ret += "..."
            else:
                ret += ch
        await set_nickname.finish(f"好哦，以后就叫你{ret}，诶，昵称太长了好像没记住...（昵称不能超过10个字）")
    if user := await NickName.filter(user_id=event.user_id).first():
        user.nickname = name
        await user.save()
    else:
        await NickName(user_id=event.user_id, nickname=name).save()
    await set_nickname.send(
        choice(
            [
                f"好啦好啦，我知道啦，{name}，以后就这么叫你吧",
                f"嗯嗯，{bot_nickname}记住你的昵称了哦，{name}",
                f"{bot_nickname}会好好记住{name}的，放心吧",
                f"好..好.，那我以后就叫你{name}了.",
            ]
        ),
        at_sender=True,
    )


@query_nickname.handle()
async def _(bot: Bot, event: MessageEvent):
    bot_nickname = list(bot.config.nickname)[0]
    if name := await NickName.filter(user_id=event.user_id).first():
        await query_nickname.finish(
            choice(
                [
                    f"我肯定记得你啊，你是{name.nickname}啊",
                    f"我不会忘记你的，你也不要忘记我！{name.nickname}",
                    f"哼哼，{bot_nickname}记忆力可是很好的，{name.nickname}",
                    f"嗯？你是失忆了嘛...{name.nickname}..",
                    f"不要小看{bot_nickname}的记忆力啊！{name.nickname}！",
                    f"哎？{name.nickname}..怎么了吗..突然这样问..",
                ]
            ),
            at_sender=True,
        )
    nickname = (await bot.get_stranger_info(user_id=event.user_id))["nickname"]
    await query_nickname.send(
        choice([f"没..没有昵称嘛，{nickname}", f"你是{nickname}？"]), at_sender=True
    )


@cancel_nickname.handle()
async def _(bot: Bot, event: MessageEvent):
    if not await NickName.filter(user_id=event.user_id):
        await cancel_nickname.finish("你还没有起昵称哦~", at_sender=True)
    bot_nickname = list(bot.config.nickname)[0]
    name = await NickName.get(user_id=event.user_id)
    await cancel_nickname.send(
        choice(
            [
                f"呜..{bot_nickname}睡一觉就会忘记的..和梦一样..{name.nickname}",
                f"我知道了..{name.nickname}..",
                f"是{bot_nickname}哪里做的不好嘛..好吧..晚安{name.nickname}",
                f"呃，{name.nickname}，下次我绝对绝对绝对不会再忘记你！",
                f"可..可恶！{name.nickname}！太可恶了！呜",
            ]
        )
    )
    # 睡一觉
    await name.delete()
