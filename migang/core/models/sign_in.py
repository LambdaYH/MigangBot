from tortoise import fields
from tortoise.models import Model


class SignIn(Model):
    user_id = fields.BigIntField(pk=True)
    signin_count = fields.IntField(default=0)
    """签到总次数
    """
    impression_diff = fields.DecimalField(12, 3, default=0)
    """好感度变动
    """
    gold_diff = fields.IntField(default=0)
    """金钱变动
    """
    windfall = fields.TextField(null=True, default=None)
    """意外效果
    """
    next_effect = fields.TextField(null=True, default=None)
    """下一次签到触发的效果
    """
    next_effect_params = fields.JSONField(null=True, default=None)
    """下一次签到时的参数
    """
    time = fields.DatetimeField(auto_now=True)
    """最后签到的时间
    """

    class Meta:
        table = "sign_in"
        table_description = "用户签到记录"
