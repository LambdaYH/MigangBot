from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "bank" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "balance" DECIMAL(20,2) NOT NULL DEFAULT 0,
    "frozen" DECIMAL(20,2) NOT NULL DEFAULT 0,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "bank" IS '用户银行账户';
        CREATE TABLE IF NOT EXISTS "chatgpt_chat_history" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "group_id" BIGINT,
    "target_id" BIGINT,
    "message" JSONB NOT NULL,
    "time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "chatgpt_chat_history" IS 'chatgpt的历史会话记录';
        CREATE TABLE IF NOT EXISTS "chatgpt_chat_impression" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "impression" VARCHAR(255) NOT NULL,
    "time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "chatgpt_chat_impression" IS 'chatgpt的印象记录';
        CREATE TABLE IF NOT EXISTS "feedback" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "content" TEXT NOT NULL,
    "time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "feedback" IS '用户反馈记录';
        CREATE TABLE IF NOT EXISTS "goods_group" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_id" BIGINT NOT NULL,
    "goods_id" INT NOT NULL,
    "count" INT NOT NULL DEFAULT 0
);
COMMENT ON TABLE "goods_group" IS '群物品信息';
        CREATE TABLE IF NOT EXISTS "goods_info" (
    "goods_id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "description" TEXT,
    "price" DECIMAL(10,2) NOT NULL,
    "type" VARCHAR(32) NOT NULL,
    "extra" JSONB
);
COMMENT ON TABLE "goods_info" IS '物品信息表';
        CREATE TABLE IF NOT EXISTS "goods_use_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "goods_id" INT NOT NULL,
    "count" INT NOT NULL DEFAULT 1,
    "time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "goods_use_log" IS '物品使用记录';
        CREATE TABLE IF NOT EXISTS "group_status" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_id" BIGINT NOT NULL UNIQUE,
    "permission" SMALLINT NOT NULL,
    "bot_status" BOOL NOT NULL DEFAULT True
);
COMMENT ON COLUMN "group_status"."permission" IS 'BLACK: 1
BAD: 2
NORMAL: 3
GOOD: 4
EXCELLENT: 5';
COMMENT ON TABLE "group_status" IS '管理群相关状态';
        CREATE TABLE IF NOT EXISTS "group_welcome" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_id" BIGINT NOT NULL,
    "welcome_message" TEXT
);
COMMENT ON TABLE "group_welcome" IS '群欢迎语信息';
        CREATE TABLE IF NOT EXISTS "shop_group_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_id" BIGINT NOT NULL,
    "goods_id" INT NOT NULL,
    "count" INT NOT NULL DEFAULT 1,
    "time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "shop_group_log" IS '群商店购买记录';
        CREATE TABLE IF NOT EXISTS "shop_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "goods_id" INT NOT NULL,
    "count" INT NOT NULL DEFAULT 1,
    "time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "shop_log" IS '用户商店购买记录';
        CREATE TABLE IF NOT EXISTS "sign_in" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "sign_in_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "reward" DECIMAL(10,2) NOT NULL DEFAULT 0
);
COMMENT ON TABLE "sign_in" IS '用户签到记录';
        CREATE TABLE IF NOT EXISTS "transaction_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "target_id" BIGINT NOT NULL,
    "amount" DECIMAL(20,2) NOT NULL DEFAULT 0,
    "time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "transaction_log" IS '用户交易记录';
        CREATE TABLE IF NOT EXISTS "user_bag" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "goods_id" INT NOT NULL,
    "count" INT NOT NULL DEFAULT 0,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "user_bag" IS '用户背包信息';
        CREATE TABLE IF NOT EXISTS "user_property" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "property_name" VARCHAR(64) NOT NULL,
    "property_value" VARCHAR(255),
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "user_property" IS '用户属性信息';
        CREATE TABLE IF NOT EXISTS "user_status" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "status" VARCHAR(32) NOT NULL
);
COMMENT ON TABLE "user_status" IS '用户状态信息';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "goods_group";
        DROP TABLE IF EXISTS "bank";
        DROP TABLE IF EXISTS "group_status";
        DROP TABLE IF EXISTS "chatgpt_chat_history";
        DROP TABLE IF EXISTS "transaction_log";
        DROP TABLE IF EXISTS "shop_group_log";
        DROP TABLE IF EXISTS "user_property";
        DROP TABLE IF EXISTS "goods_info";
        DROP TABLE IF EXISTS "goods_use_log";
        DROP TABLE IF EXISTS "user_status";
        DROP TABLE IF EXISTS "sign_in";
        DROP TABLE IF EXISTS "group_welcome";
        DROP TABLE IF EXISTS "feedback";
        DROP TABLE IF EXISTS "chatgpt_chat_impression";
        DROP TABLE IF EXISTS "user_bag";
        DROP TABLE IF EXISTS "shop_log";"""


MODELS_STATE = (
    "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"
    "k5z8f/AYc7w6k="
)
