from tortoise import fields
from tortoise.models import Model
from tortoise.indexes import Index
from tortoise.transactions import in_transaction

from .migang_id import MigangId


class PlatformId(Model):
    platform = fields.TextField(null=False)
    user_id = fields.TextField(null=True)
    group_id = fields.TextField(null=True)
    migang_id = fields.IntField(null=False)

    class Meta:
        table = "platform_id"
        table_description = "平台各id与米缸id的对应"
        unique_together = ("platform", "user_id", "group_id")

    @classmethod
    async def extract_migang_group_id(cls, platform: str, group_id: str) -> int:
        if (
            target := await cls.filter(group_id=group_id, platform=platform)
            .first()
            .values_list("migang_id")
        ) and (target[0] is not None):
            return target[0]
        else:
            async with in_transaction() as connection:
                new_id = await MigangId.get_next_id(connection=connection)
                await cls(
                    platform=platform,
                    group_id=group_id,
                    migang_id=new_id,
                ).save(using_db=connection)
                return new_id

    @classmethod
    async def extract_migang_user_id(cls, platform: str, user_id: str) -> int:
        if (
            target := await cls.filter(user_id=user_id, platform=platform)
            .first()
            .values_list("migang_id")
        ) and (target[0] is not None):
            return target[0]
        else:
            async with in_transaction() as connection:
                new_id = await MigangId.get_next_id(connection=connection)
                await cls(
                    platform=platform,
                    user_id=user_id,
                    migang_id=new_id,
                ).save(using_db=connection)
                return new_id
