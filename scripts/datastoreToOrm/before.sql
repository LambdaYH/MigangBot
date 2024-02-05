-- chatrecord --
ALTER TABLE "public"."nonebot_plugin_chatrecorder_messagerecord" RENAME TO "nonebot_plugin_chatrecorder_messagerecord_old";
DROP TABLE IF EXISTS "public"."nonebot_plugin_chatrecorder_alembic_version";

-- session --
ALTER TABLE "public"."nonebot_plugin_session_sessionmodel" RENAME CONSTRAINT "unique_session" TO "unique_session_old";

-- wordcloud --
ALTER TABLE "public"."nonebot_plugin_wordcloud_schedule" RENAME TO "nonebot_plugin_wordcloud_schedule_old";
DROP TABLE IF EXISTS "public"."nonebot_plugin_wordcloud_alembic_version";

-- shidan --
ALTER TABLE "public"."nonebot_plugin_shindan_shindanrecord" RENAME TO "nonebot_plugin_shindan_shindanrecord_old";
DROP TABLE IF EXISTS "public"."nonebot_plugin_shindan_alembic_version";
