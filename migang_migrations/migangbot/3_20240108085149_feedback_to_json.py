from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "feedback" ALTER COLUMN "content" TYPE JSONB USING "content"::JSONB;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "feedback" ALTER COLUMN "content" TYPE TEXT USING "content"::TEXT;"""
