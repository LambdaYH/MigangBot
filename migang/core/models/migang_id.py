from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Max
from tortoise.backends.base.client import BaseDBAsyncClient


class MigangId(Model):
    id = fields.IntField(pk=True)

    class Meta:
        table = "migang_id"
        table_description = "唯一的米缸ID"

    @classmethod
    async def get_next_id(cls, connection: BaseDBAsyncClient | None) -> int:
        await cls.save(using_db=connection)
        return (
            await cls.all()
            .using_db(connection)
            .annotate(max_id=Max("id"))
            .first()
            .values_list("max_id")
        )[0]
