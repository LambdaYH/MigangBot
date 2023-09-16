from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Max
from tortoise.backends.base.client import BaseDBAsyncClient


class MigangId(Model):
    id = fields.IntField(pk=True)
    value = fields.IntField(null=True)

    class Meta:
        table = "migang_id"
        table_description = "唯一的米缸ID"

    @classmethod
    async def get_next_id(cls, connection: BaseDBAsyncClient | None) -> int:
        item = await cls.filter(id=1).using_db(connection).first()
        if item is None:
            item = cls(value=0)
        else:
            item.value += 1
        await item.save(using_db=connection)
        return item.value
