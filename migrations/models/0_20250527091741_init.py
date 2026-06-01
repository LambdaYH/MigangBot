from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJy1lO1P2zAQxv+VKp9AYhOE8iK+lUrTQKxIMKZJqIqusZtaOHawLxsI5X/n7Lw4FAJoWj"
    "9Vfu763JPfOXmKcs24tF8n3Ih0FZ2MniIoCvptCtHOKFKQ86C0rVRAWEhfgU4SivEHbkm8"
    "ndMxBwUZZ3RUpZQkwMKigRRJWYK0nKTiLlkKLpkf3s4SzLmVStyX7oymdK2ML6GUGOzqcS"
    "x0OL1J1fqzRZJqWeYq+DKdUgyhsuCUccUNYN/Lp0rwsfCJzhR+8zGpkmrlHkMotD515jq+"
    "xHvjo/Hx/uH4mFp8hE45qnx6mxpRoNAqzC0ecaVVN4UsozpzmF7P8BlmP6OqevsBlg3GwD"
    "7O1xQd6zWFAUJPCvz/cGNdzv4SOqDDW2hbPlpDz/6DXbR/f7mM6QrM4DZyeEgkVxm6+xwf"
    "HHyWPZm8w/7X5Gr6fXK1RYbbrk3TNa5v/6wpxXXNLSiAdG/ThiA21hsGuLe7+38BkuEgQF"
    "97CZDCIa/fik1A7Nn/E8jz68vZEMjPcrtRVL1lIsWdkRQW5+9QdPNcObf2Xvbhbf2Y/F7n"
    "Or24PHVSoS1mxrt4g1NiPB8KV1NOUGccV9y0n4oFpHd/wbDk1Yemq6x9X6rqGdEsByE="
)
