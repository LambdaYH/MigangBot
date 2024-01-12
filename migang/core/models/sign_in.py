from typing import List
from datetime import datetime, timedelta

from tortoise import fields
from tortoise.models import Model

from migang.core.constant import ID_MAX_LENGTH


class SignIn(Model):
    user_id = fields.CharField(max_length=ID_MAX_LENGTH, null=False)
    signin_count = fields.IntField(default=0)
    """签到总次数
    """
    impression_diff = fields.DecimalField(12, 3, default=0)
    """好感度变动
    """
    gold_diff = fields.IntField(null=False, default=0)
    """金钱变动
    """
    windfall = fields.TextField(null=False, default="")
    """意外效果
    """
    next_effect: List[str] = fields.JSONField(null=False, default=[])
    """下一次签到触发的效果，列表形式，可以通过别的手段追加
    """
    next_effect_params = fields.JSONField(null=False, default=[])
    """下一次签到时的参数
    """
    time = fields.DatetimeField(auto_now=True)
    """最后签到的时间
    """

    class Meta:
        table = "sign_in"
        table_description = "用户签到记录"

    @classmethod
    async def add_next_effect(cls, user_id: int, effect: str, **kwargs) -> bool:
        user = await cls.filter(user_id=user_id).first()
        if not user:
            user = cls(
                user_id=user_id, next_effect=[effect], next_effect_params=[kwargs]
            )
            await user.save()
            await user.update_from_dict({"time": datetime.now() - timedelta(days=12)})
            return
        if effect in user.next_effect:
            return False
        user.next_effect.append(effect)
        user.next_effect_params.append(kwargs)
        await user.save(update_fields=["next_effect", "next_effect_params"])
        return True
