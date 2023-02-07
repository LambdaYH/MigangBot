from tortoise import fields
from tortoise.models import Model


class NickName(Model):
    user_id = fields.BigIntField(pk=True)
    nickname = fields.TextField(null=False)
