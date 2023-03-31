from nonebot import on_fullmatch
from nonebot.adapters.onebot.v11 import Bot

aaa = on_fullmatch("测试测试")

@aaa.handle()
async def _(bot:Bot):
    group_bot_info = await bot.get_group_member_info(
                group_id=user, user_id=int(bot.self_id), no_cache=True
            )  # 调用api获取群内bot的相关参数