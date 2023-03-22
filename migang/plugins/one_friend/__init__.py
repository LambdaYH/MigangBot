import random
from io import BytesIO
from typing import Any, Tuple, Optional

from nonebot import on_regex
from pil_utils import BuildImage
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupMessageEvent

from migang.utils.image import get_user_avatar

__plugin_meta__ = PluginMetadata(
    name="我有一个朋友",
    description="我有一个朋友说xxxx",
    usage=f"""
指令：
    我有一个朋友想问问 [文本] [at]: 当at时你的朋友就是艾特对象（但是有可能会反弹
""".strip(),
    extra={
        "unique_name": "migang_one_friend",
        "example": "",
        "author": "migang",
        "version": "0.0.1",
    },
)

__plugin_category__ = "好玩的"

one_friend = on_regex(
    "^我.{0,4}朋友.{0,2}(?:想问问|说|让我问问|想问|让我问|想知道|让我帮他问问|让我帮他问|让我帮忙问|让我帮忙问问|问)(.{0,30})$",
    priority=5,
    block=True,
)


@one_friend.handle()
async def _(
    bot: Bot, event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()
):
    target_user: Optional[int] = None
    for seg in event.message:
        if seg.type == "at":
            target_user = seg.data["qq"]
            break
    if not target_user:
        target_user = random.choice(
            [
                user["user_id"]
                for user in await bot.get_group_member_list(group_id=event.group_id)
            ]
        )
        user_name = "朋友"
    else:
        if random.random() < 0.20:
            target_user = event.user_id
        at_user = await bot.get_group_member_info(
            group_id=event.group_id, user_id=target_user
        )
        user_name = at_user.get("card") or at_user["nickname"]
    msg = Message(reg_group[0]).extract_plain_text().strip()
    if not msg:
        msg = "我...要说什么？"
    msg = msg.replace("他", "我").replace("她", "我").replace("它", "我")
    x = await get_user_avatar(target_user)
    if x:
        ava = BuildImage.open(BytesIO(x)).resize((100, 100))
    else:
        ava = BuildImage.new("RGBA", (100, 100), color=(0, 0, 0))
    ava = ava.circle()
    text = BuildImage.new("RGBA", (400, 40), color="white")
    text.draw_text((0, 0), user_name, fontsize=30, fontname="Microsoft YaHei")
    A = BuildImage.new("RGBA", (700, 150), color="white")
    A.paste(ava, (30, 25), True)
    A.paste(text, (150, 28))
    A.draw_text(
        (150, 85), msg, fontsize=25, fill=(125, 125, 125), fontname="Microsoft YaHei"
    )

    await one_friend.send(MessageSegment.image(A.save_png()))
