import jieba
from io import BytesIO
from typing import List, Tuple, Optional, Dict

from anyio import to_thread
from wordcloud import WordCloud
from nonebot_plugin_wordcloud.config import global_config, plugin_config
from nonebot_plugin_wordcloud.data_source import get_mask, pre_precess


def analyse_message(msg: str) -> Dict[str, float]:
    """分析消息

    分词，并统计词频
    """
    # 设置停用词表
    if plugin_config.wordcloud_stopwords_path:
        jieba.analyse.set_stop_words(plugin_config.wordcloud_stopwords_path)
    # 加载用户词典
    if plugin_config.wordcloud_userdict_path:
        jieba.load_userdict(str(plugin_config.wordcloud_userdict_path))
    # 基于 TF-IDF 算法的关键词抽取
    # 返回所有关键词，因为设置了数量其实也只是 tags[:topK]，不如交给词云库处理
    words = jieba.analyse.extract_tags(msg, topK=30, withWeight=True)
    return {word: weight for word, weight in words}


def _get_wordcloud_and_hot_words(
    messages: List[str], mask_key: Optional[str] = None
) -> Optional[Tuple[List[str], BytesIO]]:
    # 过滤掉命令
    command_start = tuple([i for i in global_config.command_start if i])
    message = " ".join([m for m in messages if not m.startswith(command_start)])
    # 预处理
    message = pre_precess(message)
    # 分析消息。分词，并统计词频
    frequency = analyse_message(message)

    # 获取前三的词
    if len(frequency) < 3:
        return None
    top_words = []
    for i, k in enumerate(list(frequency.keys())[:3]):
        top_words.append(f"Top {i}: {k}")
    try:
        wordcloud = WordCloud(
            font_path=str(plugin_config.wordcloud_font_path),
            width=plugin_config.wordcloud_width,
            height=plugin_config.wordcloud_height,
            background_color=plugin_config.wordcloud_background_color,
            colormap=plugin_config.wordcloud_colormap,
            mask=get_mask(mask_key),
        )
        image = wordcloud.generate_from_frequencies(frequency).to_image()
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        return top_words, image_bytes
    except ValueError:
        pass


async def get_wordcloud_and_hot_words(
    messages: List[str], mask_key: Optional[str] = None
) -> Optional[Tuple[List[str], BytesIO]]:
    return await to_thread.run_sync(_get_wordcloud_and_hot_words, messages, mask_key)
