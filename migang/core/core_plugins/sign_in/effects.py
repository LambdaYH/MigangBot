import random
from decimal import Decimal

from migang.core.decorator import sign_in_effect
from migang.core.models import SignIn, UserProperty


@sign_in_effect(weight=10, name="什么事都没发生")
async def _():
    return "......"


@sign_in_effect(weight=5, name="捡到钱了")
async def _(user_sign_in: SignIn, user_prop: UserProperty):
    random_gold = random.randint(0, 100)
    user_prop.gold += random_gold
    user_sign_in.gold_diff += random_gold

    return f"额外获得了{random_gold}块金币！"


@sign_in_effect(weight=3, name="本次签到好感度翻倍")
async def _(user_sign_in: SignIn, user_prop: UserProperty):
    impression_diff = user_sign_in.impression_diff
    user_prop.impression += Decimal(impression_diff)
    user_sign_in.impression_diff *= 2

    return "本次签到好感度翻倍！"


@sign_in_effect(weight=3, name="下一次签到好感度双倍")
async def _():
    return "下一次见面时，好感度翻倍~"


@sign_in_effect.next(name="下一次签到好感度双倍")
async def _(user_sign_in: SignIn, user_prop: UserProperty):
    impression_diff = user_sign_in.impression_diff
    user_prop.impression += Decimal(impression_diff)
    user_sign_in.impression_diff *= 2


@sign_in_effect(weight=1, name="本次签到好感度三倍")
async def _(user_sign_in: SignIn, user_prop: UserProperty):
    impression_diff = user_sign_in.impression_diff
    user_prop.impression += Decimal(impression_diff) * 2
    user_sign_in.impression_diff *= 3

    return "本次签到好感度三倍！"
