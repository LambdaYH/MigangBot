from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message, Bot
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
import random
import asyncio

__plugin_meta__ = PluginMetadata(
    name="roll",
    description="犹豫不决吗？那就让我帮你决定吧",
    usage="""
usage：
    随机数字 或 随机选择事件
    指令：
        roll: 随机 0-100 的数字
        roll *[文本]: 随机事件
        示例：roll 吃饭 睡觉 打游戏
""".strip(),
    extra={
        "unique_name": "migang_roll",
        "example": "",
        "author": "HibiKier",
        "version": 0.1,
    },
)

roll = on_command("roll", priority=5, block=True)


@roll.handle()
async def _(
    matcher: Matcher, bot: Bot, event: MessageEvent, arg: Message = CommandArg()
):
    msg = arg.extract_plain_text().strip().split()
    if not msg:
        await roll.finish(f"roll: {random.randint(0, 100)}", at_sender=True)
    if msg and len(msg) < 2:
        matcher.block = False
        await roll.finish()
    user_name = event.sender.card or event.sender.nickname
    await roll.send(
        random.choice(
            [
                "转动命运的齿轮，拨开眼前迷雾...",
                f"启动吧，命运的水晶球，为{user_name}指引方向！",
                "嗯哼，在此刻转动吧！命运！",
                f"在此祈愿，请为{user_name}降下指引...",
            ]
        )
    )
    await asyncio.sleep(1)
    x = random.choice(msg)
    await roll.send(
        random.choice(
            [
                f"让{list(bot.config.nickname)[0]}看看是什么结果！答案是：{x}",
                f"根据命运的指引，接下来{user_name} {x} 会比较好",
                f"祈愿被回应了！是 {x}！",
                f"结束了，{user_name}，命运之轮停在了 {x}！",
            ]
        )
    )
