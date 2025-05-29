import os
from typing import List, Optional

from nonebot.log import logger

from migang.core.path import DATA_PATH
from migang.core.manager import plugin_manager
from migang.core.utils.config_operation import sync_get_config, post_init_manager

try:
    import chromadb
    from openai import AsyncOpenAI
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    AsyncOpenAI = None

# 配置项
EMBEDDING_MODEL = sync_get_config("embedding_model", "chat_chatgpt", None)
OPENAI_API_KEY = sync_get_config("api_keys", "chat_chatgpt", None)
OPENAI_API_BASE = sync_get_config("api_base", "chat_chatgpt", None)

# 向量库初始化
chroma_client = None
collection = None
if chromadb and EMBEDDING_MODEL and OPENAI_API_KEY:
    chroma_client = chromadb.Client(
        Settings(
            persist_directory=str(DATA_PATH / "plugin_vector"),
            anonymized_telemetry=False,
        )
    )
    collection = chroma_client.get_or_create_collection("plugin_help")
    openai_client = AsyncOpenAI(
        api_key=OPENAI_API_KEY[0]
        if isinstance(OPENAI_API_KEY, list)
        else OPENAI_API_KEY,
        base_url=OPENAI_API_BASE or None,
    )
else:
    openai_client = None


def get_plugin_text(plugin) -> str:
    """拼接插件信息为文本用于 embedding"""
    info = [
        f"插件名: {plugin.name}",
        f"别名: {', '.join(plugin.all_name) if hasattr(plugin, 'all_name') else ''}",
        f"分类: {plugin.category or ''}",
        f"作者: {plugin.author or ''}",
        f"版本: {plugin.version or ''}",
        f"用法: {plugin.usage or ''}",
    ]
    return "\n".join(info)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """批量获取文本 embedding (异步，自动分批，每批最多50条)"""
    if not openai_client:
        return []
    batch_size = 50
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = await openai_client.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        all_embeddings.extend([d.embedding for d in resp.data])
    return all_embeddings


async def sync_plugin_to_vector_db():
    """同步所有插件信息到向量数据库 (异步)"""
    if not (collection and openai_client):
        return
    plugins = list(plugin_manager.get_plugin_list())
    if not plugins:
        return
    texts = [get_plugin_text(p) for p in plugins]
    ids = [p.plugin_name for p in plugins]
    embeddings = await embed_texts(texts)
    # 先删除所有旧的
    collection.delete(ids=ids)
    # 再写入
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=[{"name": p.name} for p in plugins],
    )


async def search_plugin(query: str) -> str:
    """检索最相关插件，返回详细信息文本 (同步接口，内部自动await)"""
    if not (collection and openai_client):
        return "[插件检索功能未启用]"
    query_emb = await embed_texts([query])
    if not query_emb:
        return "[embedding 失败]"
    result = collection.query(query_embeddings=query_emb, n_results=1)
    if not result["ids"] or not result["documents"]:
        return "未找到相关插件"
    return result["documents"][0][0]


@post_init_manager
async def _():
    # 启动时自动同步
    if collection and openai_client:
        logger.info("[插件向量库同步] 开始同步")
        try:
            await sync_plugin_to_vector_db()
        except Exception as e:
            logger.error(f"[插件向量库同步失败] {e}")
        logger.info("[插件向量库同步] 同步完成")
