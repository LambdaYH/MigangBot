from tortoise import fields
from tortoise.models import Model


class Bank(Model):
    user_id = fields.BigIntField(null=False)
    balance = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    frozen = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "bank"
        table_description = "用户银行账户"
