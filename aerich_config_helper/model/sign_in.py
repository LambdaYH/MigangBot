from tortoise import fields
from tortoise.models import Model


class SignIn(Model):
    user_id = fields.BigIntField(null=False)
    sign_in_time = fields.DatetimeField(auto_now_add=True)
    reward = fields.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        table = "sign_in"
        table_description = "用户签到记录"
