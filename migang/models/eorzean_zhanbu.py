from tortoise import fields
from tortoise.models import Model


class EorzeanZhanbu(Model):
    user_id = fields.BigIntField(pk=True)
    luck = fields.IntField(null=False)
    yi = fields.TextField(null=False)
    ji = fields.TextField(null=False)
    dye = fields.TextField(null=False)
    append_msg = fields.TextField(null=False)
    basemap = fields.TextField(NULL=False)
    zhanbu_time_last = fields.DatetimeField(null=False, auto_now=True)
