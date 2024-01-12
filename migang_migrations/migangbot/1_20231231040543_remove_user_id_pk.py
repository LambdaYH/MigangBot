from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "sign_in" RENAME COLUMN "user_id" TO "id";
        ALTER TABLE "sign_in" ADD "user_id" BIGINT;
        ALTER TABLE "user_property" RENAME COLUMN "user_id" TO "id";
        ALTER TABLE "user_property" ADD "user_id" BIGINT;

        CREATE TABLE IF NOT EXISTS "sign_in_temp" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "user_id" BIGINT NOT NULL,
            "signin_count" INT NOT NULL  DEFAULT 0,
            "impression_diff" DECIMAL(12,3) NOT NULL  DEFAULT 0,
            "gold_diff" INT NOT NULL  DEFAULT 0,
            "windfall" TEXT NOT NULL,
            "next_effect" JSONB NOT NULL,
            "next_effect_params" JSONB NOT NULL,
            "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO sign_in_temp (user_id, signin_count, impression_diff, gold_diff, windfall, next_effect, next_effect_params, time)
            SELECT id, signin_count, impression_diff, gold_diff, windfall, next_effect, next_effect_params, time
            FROM sign_in;

        DROP TABLE sign_in;

        ALTER TABLE sign_in_temp RENAME TO sign_in;
        COMMENT ON TABLE "sign_in" IS '用户签到记录';

        CREATE TABLE IF NOT EXISTS "user_property_temp" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "user_id" BIGINT NOT NULL,
            "nickname" TEXT,
            "gold" BIGINT NOT NULL  DEFAULT 0,
            "impression" DECIMAL(12,3) NOT NULL  DEFAULT 0
        );

        INSERT INTO user_property_temp (user_id, nickname, gold, impression)
            SELECT id, nickname, gold, impression
            FROM user_property;

        DROP TABLE user_property;

        ALTER TABLE user_property_temp RENAME TO user_property;
        COMMENT ON TABLE "user_property" IS '与用户相关的各项可变动属性记录';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "sign_in" RENAME COLUMN "id" TO "user_id";
        ALTER TABLE "sign_in" DROP COLUMN "user_id";
        ALTER TABLE "user_property" RENAME COLUMN "id" TO "user_id";
        ALTER TABLE "user_property" DROP COLUMN "user_id";

        CREATE TABLE IF NOT EXISTS "sign_in_temp" (
            "user_id" BIGSERIAL NOT NULL PRIMARY KEY,
            "signin_count" INT NOT NULL  DEFAULT 0,
            "impression_diff" DECIMAL(12,3) NOT NULL  DEFAULT 0,
            "gold_diff" INT NOT NULL  DEFAULT 0,
            "windfall" TEXT NOT NULL,
            "next_effect" JSONB NOT NULL,
            "next_effect_params" JSONB NOT NULL,
            "time" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO sign_in_temp (user_id, signin_count, impression_diff, gold_diff, windfall, next_effect, next_effect_params, time)
            SELECT user_id, signin_count, impression_diff, gold_diff, windfall, next_effect, next_effect_params, time
            FROM sign_in;

        DROP TABLE sign_in;

        ALTER TABLE sign_in_temp RENAME TO sign_in;
        COMMENT ON TABLE "sign_in" IS '用户签到记录';

        CREATE TABLE IF NOT EXISTS "user_property_temp" (
            "user_id" BIGSERIAL NOT NULL PRIMARY KEY,
            "nickname" TEXT,
            "gold" BIGINT NOT NULL  DEFAULT 0,
            "impression" DECIMAL(12,3) NOT NULL  DEFAULT 0
        );

        INSERT INTO user_property_temp (user_id, nickname, gold, impression)
            SELECT user_id, nickname, gold, impression
            FROM user_property;

        DROP TABLE user_property;

        ALTER TABLE user_property_temp RENAME TO user_property;
        COMMENT ON TABLE "user_property" IS '与用户相关的各项可变动属性记录';
    """
