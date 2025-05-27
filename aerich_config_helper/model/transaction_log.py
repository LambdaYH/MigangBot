from tortoise import fields
from tortoise.models import Model


class TransactionLog(Model):
    user_id = fields.BigIntField(null=False)
    target_id = fields.BigIntField(null=False)
    amount = fields.DecimalField(max_digits=20, decimal_places=2, default=0)
    time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "transaction_log"
        table_description = "用户交易记录"
