from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chatgpt_chat_history" ADD "is_bot" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chatgpt_chat_history" DROP COLUMN "is_bot";"""


MODELS_STATE = (
    "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"
    "eB+PqXbZGc/7/wFNEDtw"
)
