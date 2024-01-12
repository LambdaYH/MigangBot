from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "bank" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "amount" INT NOT NULL  DEFAULT 0,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deposit_type" SMALLINT NOT NULL  DEFAULT 0,
    "duration" TIMESTAMPTZ
);
COMMENT ON COLUMN "bank"."deposit_type" IS 'demand_deposit: 0\ntime_deposit: 1';
COMMENT ON TABLE "bank" IS '银行';
CREATE TABLE IF NOT EXISTS "chatgpt_chat_history" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "group_id" BIGINT,
    "target_id" BIGINT,
    "message" JSONB NOT NULL,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "chatgpt_chat_history" IS 'chatgpt的历史会话记录';
CREATE TABLE IF NOT EXISTS "chatgpt_chat_impression" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "group_id" BIGINT NOT NULL,
    "self_id" BIGINT NOT NULL,
    "impression" TEXT NOT NULL,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_chatgpt_cha_user_id_022edd" UNIQUE ("user_id", "group_id", "self_id")
);
COMMENT ON TABLE "chatgpt_chat_impression" IS 'chatgpt的对用户的印象记录，各群独立';
CREATE TABLE IF NOT EXISTS "feedback" (
    "feedback_id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "group_id" BIGINT,
    "content" TEXT NOT NULL,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "feedback" IS '用户反馈记录';
CREATE TABLE IF NOT EXISTS "goods_group" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "purchase_limit" INT,
    "use_limit" INT
);
COMMENT ON TABLE "goods_group" IS '商品组信息';
CREATE TABLE IF NOT EXISTS "goods_info" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "price" INT NOT NULL,
    "description" TEXT NOT NULL,
    "discount" DOUBLE PRECISION NOT NULL  DEFAULT 1,
    "purchase_limit" INT,
    "use_limit" INT,
    "group" JSONB,
    "on_shelf" BOOL NOT NULL  DEFAULT True
);
COMMENT ON TABLE "goods_info" IS '商品信息';
CREATE TABLE IF NOT EXISTS "goods_use_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "goods_name" TEXT NOT NULL,
    "amount" INT NOT NULL  DEFAULT 1,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "goods_use_log" IS '商品使用日志';
CREATE TABLE IF NOT EXISTS "group_status" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_id" BIGINT NOT NULL UNIQUE,
    "permission" SMALLINT NOT NULL,
    "bot_status" BOOL NOT NULL  DEFAULT True
);
COMMENT ON COLUMN "group_status"."permission" IS 'BLACK: 1\nBAD: 2\nNORMAL: 3\nGOOD: 4\nEXCELLENT: 5';
COMMENT ON TABLE "group_status" IS '管理群相关状态';
CREATE TABLE IF NOT EXISTS "group_welcome" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_id" BIGINT NOT NULL,
    "content" JSONB,
    "status" BOOL NOT NULL  DEFAULT True
);
COMMENT ON TABLE "group_welcome" IS '群欢迎语';
CREATE TABLE IF NOT EXISTS "shop_group_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "group_name" VARCHAR(255) NOT NULL,
    "amount" INT NOT NULL,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "shop_group_log" IS '商品组购买/退货记录';
CREATE TABLE IF NOT EXISTS "shop_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "item_name" VARCHAR(255) NOT NULL,
    "amount" INT NOT NULL,
    "price" DOUBLE PRECISION NOT NULL,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "shop_log" IS '商店购买/退货记录';
CREATE TABLE IF NOT EXISTS "sign_in" (
    "user_id" BIGSERIAL NOT NULL PRIMARY KEY,
    "signin_count" INT NOT NULL  DEFAULT 0,
    "impression_diff" DECIMAL(12,3) NOT NULL  DEFAULT 0,
    "gold_diff" INT NOT NULL  DEFAULT 0,
    "windfall" TEXT NOT NULL,
    "next_effect" JSONB NOT NULL,
    "next_effect_params" JSONB NOT NULL,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "sign_in" IS '用户签到记录';
CREATE TABLE IF NOT EXISTS "transaction_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "gold_earned" INT NOT NULL  DEFAULT 0,
    "gold_spent" INT NOT NULL  DEFAULT 0,
    "description" TEXT,
    "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "transaction_log" IS '交易日志';
CREATE TABLE IF NOT EXISTS "user_bag" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL,
    "item_name" VARCHAR(255) NOT NULL,
    "amount" INT NOT NULL  DEFAULT 0,
    CONSTRAINT "uid_user_bag_user_id_ff1af5" UNIQUE ("user_id", "item_name")
);
COMMENT ON TABLE "user_bag" IS '用户背包';
CREATE TABLE IF NOT EXISTS "user_property" (
    "user_id" BIGSERIAL NOT NULL PRIMARY KEY,
    "nickname" TEXT,
    "gold" BIGINT NOT NULL  DEFAULT 0,
    "impression" DECIMAL(12,3) NOT NULL  DEFAULT 0
);
COMMENT ON TABLE "user_property" IS '与用户相关的各项可变动属性记录';
CREATE TABLE IF NOT EXISTS "user_status" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "user_id" BIGINT NOT NULL UNIQUE,
    "permission" SMALLINT NOT NULL
);
COMMENT ON COLUMN "user_status"."permission" IS 'BLACK: 1\nBAD: 2\nNORMAL: 3\nGOOD: 4\nEXCELLENT: 5';
COMMENT ON TABLE "user_status" IS '管理用户相关状态';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
