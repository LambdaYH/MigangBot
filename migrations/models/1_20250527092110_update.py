from tortoise import BaseDBAsyncClient


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
COMMENT ON COLUMN "group_status"."permission" IS 'BLACK: 1\nBAD: 2\nNORMAL: 3\nGOOD: 4\nEXCELLENT: 5';
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
