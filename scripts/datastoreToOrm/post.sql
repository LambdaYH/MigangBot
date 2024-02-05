-- shidan --
INSERT INTO nonebot_plugin_shindan_shindanrecord SELECT * from nonebot_plugin_shindan_shindanrecord_old WHERE id > 10;

-- session --
DROP TABLE IF EXISTS "public"."nonebot_plugin_session_sessionmodel";
DROP TABLE IF EXISTS "public"."nonebot_plugin_session_alembic_version";

-- chatrecord --
INSERT INTO "nonebot_plugin_chatrecorder_messagerecord" (id, session_persist_id, time, type, message_id, message, plain_text) SELECT id, session_id, time, type, message_id, message, plain_text from nonebot_plugin_chatrecorder_messagerecord_old;
DROP TABLE IF EXISTS "public"."nonebot_plugin_chatrecorder_messagerecord_old";

-- wordcloud --
INSERT INTO "nonebot_plugin_wordcloud_schedule" SELECT id, target, time from nonebot_plugin_wordcloud_schedule_old;
DROP TABLE IF EXISTS "public"."nonebot_plugin_wordcloud_schedule_old";
