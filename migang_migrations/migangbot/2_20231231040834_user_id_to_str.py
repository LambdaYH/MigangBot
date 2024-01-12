from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "bank" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "chatgpt_chat_history" ALTER COLUMN "target_id" TYPE VARCHAR(16) USING "target_id"::VARCHAR(16);
        ALTER TABLE "chatgpt_chat_history" ALTER COLUMN "group_id" TYPE VARCHAR(16) USING "group_id"::VARCHAR(16);
        ALTER TABLE "chatgpt_chat_history" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "chatgpt_chat_impression" ALTER COLUMN "self_id" TYPE VARCHAR(16) USING "self_id"::VARCHAR(16);
        ALTER TABLE "chatgpt_chat_impression" ALTER COLUMN "group_id" TYPE VARCHAR(16) USING "group_id"::VARCHAR(16);
        ALTER TABLE "chatgpt_chat_impression" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "feedback" ALTER COLUMN "group_id" TYPE VARCHAR(16) USING "group_id"::VARCHAR(16);
        ALTER TABLE "feedback" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "goods_use_log" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "group_status" ALTER COLUMN "group_id" TYPE VARCHAR(16) USING "group_id"::VARCHAR(16);
        ALTER TABLE "group_welcome" ALTER COLUMN "group_id" TYPE VARCHAR(16) USING "group_id"::VARCHAR(16);
        ALTER TABLE "shop_group_log" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "shop_log" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "sign_in" ALTER COLUMN "user_id" SET NOT NULL;
        ALTER TABLE "sign_in" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "transaction_log" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "user_bag" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "user_property" ALTER COLUMN "user_id" SET NOT NULL;
        ALTER TABLE "user_property" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);
        ALTER TABLE "user_status" ALTER COLUMN "user_id" TYPE VARCHAR(16) USING "user_id"::VARCHAR(16);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "bank" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "sign_in" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "sign_in" ALTER COLUMN "user_id" DROP NOT NULL;
        ALTER TABLE "shop_log" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_bag" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "feedback" ALTER COLUMN "group_id" TYPE BIGINT USING "group_id"::BIGINT;
        ALTER TABLE "feedback" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_status" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "goods_use_log" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "group_status" ALTER COLUMN "group_id" TYPE BIGINT USING "group_id"::BIGINT;
        ALTER TABLE "group_welcome" ALTER COLUMN "group_id" TYPE BIGINT USING "group_id"::BIGINT;
        ALTER TABLE "shop_group_log" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_property" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "user_property" ALTER COLUMN "user_id" DROP NOT NULL;
        ALTER TABLE "transaction_log" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "chatgpt_chat_history" ALTER COLUMN "target_id" TYPE BIGINT USING "target_id"::BIGINT;
        ALTER TABLE "chatgpt_chat_history" ALTER COLUMN "group_id" TYPE BIGINT USING "group_id"::BIGINT;
        ALTER TABLE "chatgpt_chat_history" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;
        ALTER TABLE "chatgpt_chat_impression" ALTER COLUMN "self_id" TYPE BIGINT USING "self_id"::BIGINT;
        ALTER TABLE "chatgpt_chat_impression" ALTER COLUMN "group_id" TYPE BIGINT USING "group_id"::BIGINT;
        ALTER TABLE "chatgpt_chat_impression" ALTER COLUMN "user_id" TYPE BIGINT USING "user_id"::BIGINT;"""
