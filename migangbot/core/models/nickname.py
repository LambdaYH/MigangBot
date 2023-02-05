from tortoise import fields
from tortoise.models import Model


class NickName(Model):
    id = fields.BigIntField(pk=True)
    name = fields.TextField()
