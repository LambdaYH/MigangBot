from sqlalchemy import BigInteger, select
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy.ext.asyncio.session import AsyncSession

Model = get_plugin_data().Model


class RussianUser(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    group_id: Mapped[int] = mapped_column(BigInteger)
    win_count: Mapped[int] = mapped_column(default=0)
    fail_count: Mapped[int] = mapped_column(default=0)
    make_money: Mapped[int] = mapped_column(default=0)
    lose_money: Mapped[int] = mapped_column(default=0)
    winning_streak: Mapped[int] = mapped_column(default=0)
    losing_streak: Mapped[int] = mapped_column(default=0)
    max_winning_streak: Mapped[int] = mapped_column(default=0)
    max_losing_streak: Mapped[int] = mapped_column(default=0)

    @classmethod
    async def add_count(
        cls, user_id: int, group_id: int, itype: str, session: AsyncSession
    ):
        """
        说明:
            添加用户输赢次数
        说明:
            :param user_qq: qq号
            :param group_id: 群号
            :param itype: 输或赢 'win' or 'lose'
        """
        user = await session.scalar(
            select(cls).where(cls.user_id == user_id, cls.group_id == group_id)
        )
        if not user:
            user = cls(user_id=user_id, group_id=group_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        if itype == "win":
            _max = (
                user.max_winning_streak
                if user.max_winning_streak > user.winning_streak + 1
                else user.winning_streak + 1
            )
            user.win_count = user.win_count + 1
            user.winning_streak = user.winning_streak + 1
            user.losing_streak = 0
            user.max_winning_streak = _max
        elif itype == "lose":
            _max = (
                user.max_losing_streak
                if user.max_losing_streak > user.losing_streak + 1
                else user.losing_streak + 1
            )
            user.fail_count = user.fail_count + 1
            user.losing_streak = user.losing_streak + 1
            user.winning_streak = 0
            user.max_losing_streak = _max
        await session.commit()

    @classmethod
    async def money(
        cls, user_id: int, group_id: int, itype: str, count: int, session: AsyncSession
    ) -> bool:
        """
        说明:
            添加用户输赢金钱
        参数:
            :param user_qq: qq号
            :param group_id: 群号
            :param itype: 输或赢 'win' or 'lose'
            :param count: 金钱数量
        """
        user = await session.scalar(
            select(cls).where(cls.user_id == user_id, cls.group_id == group_id)
        )
        if not user:
            user = cls(user_id=user_id, group_id=group_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        if itype == "win":
            user.make_money = user.make_money + count
        elif itype == "lose":
            user.lose_money = user.lose_money + count
        await session.commit()
