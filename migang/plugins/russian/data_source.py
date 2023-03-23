from typing import Optional

import pygal
from pygal.style import Style
from sqlalchemy import select
from nonebot.adapters.onebot.v11 import Bot
from sqlalchemy.ext.asyncio.session import AsyncSession

from .model import RussianUser

style = Style(font_family="Noto Sans Mono CJK SC", colors=["#B6DCEF"])


async def rank(
    bot: Bot, group_id: int, itype: str, num: int, session: AsyncSession
) -> Optional[bytes]:
    all_users = (
        await session.scalars(
            select(RussianUser).where(RussianUser.group_id == group_id)
        )
    ).all()
    if not all_users:
        return None
    all_users = {user.user_id: user for user in all_users}
    group_member = await bot.get_group_member_list(group_id=group_id)
    group_member_name = {
        member["user_id"]: member.get("card") or member["nickname"]
        for member in group_member
    }
    for user in list(all_users):
        if user not in group_member_name:
            all_users.pop(user)
    if itype == "win_rank":
        rank_name = "胜场排行榜"
        all_user_data = [user.win_count for user in all_users.values()]
    elif itype == "lose_rank":
        rank_name = "败场排行榜"
        all_user_data = [user.fail_count for user in all_users.values()]
    elif itype == "make_money":
        rank_name = "赢取金币排行榜"
        all_user_data = [user.make_money for user in all_users.values()]
    elif itype == "spend_money":
        rank_name = "输掉金币排行榜"
        all_user_data = [user.lose_money for user in all_users.values()]
    elif itype == "max_winning_streak":
        rank_name = "最高连胜排行榜"
        all_user_data = [user.max_winning_streak for user in all_users.values()]
    else:
        rank_name = "最高连败排行榜"
        all_user_data = [user.max_losing_streak for user in all_users.values()]

    user_names = [group_member_name[user] for user in all_users]
    user_data, user_names = (
        list(t)
        for t in zip(*sorted(zip(all_user_data, user_names), reverse=True)[:num])
    )
    bar_chart = pygal.Bar(style=style)
    bar_chart.title = rank_name
    bar_chart.x_labels = user_names
    bar_chart.y_labels = range(user_data[0] + 1)
    bar_chart.add(None, user_data)
    return bar_chart.render_to_png()
