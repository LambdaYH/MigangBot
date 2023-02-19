from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring

from azure.cognitiveservices.speech import (
    AudioDataStream,
    SpeechConfig,
    SpeechSynthesisOutputFormat,
    SpeechSynthesizer,
)
from nonebot import get_driver

from migang.core import get_config
from migang.core.manager import ConfigItem, config_manager

speech_config: Optional[SpeechConfig] = None
synthesizer: Optional[SpeechSynthesizer] = None
azure_tts_status = False
"""正确配置后将会为True，用以判断tts状态
"""


def status() -> bool:
    """azure tts 的配置情况

    Returns:
        bool: 若可启用则返回True
    """
    return azure_tts_status


@get_driver().on_startup
async def _():
    await config_manager.add_configs(
        "azure_tts",
        configs=(
            ConfigItem(
                key="key",
                initial_value=None,
                description="参照下面链接获取\nhttps://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-apis-create-account#get-the-keys-for-your-resource",
            ),
            ConfigItem(
                key="region",
                initial_value="southeastasia",
                description="区域",
            ),
        ),
    )
    if key := await get_config(key="key", plugin_name="azure_tts"):
        global speech_config, synthesizer, azure_tts_status
        speech_config = SpeechConfig(
            subscription=key,
            region=await get_config(key="region", plugin_name="azure_tts"),
        )
        speech_config.set_speech_synthesis_output_format(
            SpeechSynthesisOutputFormat["Audio16Khz128KBitRateMonoMp3"]
        )
        synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        azure_tts_status = True


def create_xml():
    speak = Element("speak")
    speak.set("version", "1.0")
    speak.set("xmlns", "http://www.w3.org/2001/10/synthesis")
    speak.set("xmlns:mstts", "https://www.w3.org/2001/mstts")
    speak.set("xml:lang", "zh-CN")
    voice = SubElement(speak, "voice")
    voice.set("name", "zh-CN-XiaoxiaoNeural")
    mstts = SubElement(voice, "mstts:express-as")
    mstts.set("style", "chat")
    prosody = SubElement(mstts, "prosody")
    prosody.set("rate", "0.9")

    return speak, prosody


doc, text_node = create_xml()


async def get_sound(text):
    text_node.text = text
    result = synthesizer.speak_ssml_async(tostring(doc).decode()).get()
    res = bytes()
    stream = AudioDataStream(result)
    temp = bytes(32000)
    while (filled_size := stream.read_data(temp)) > 0:
        res += temp[:filled_size]
        temp = bytes(32000)
    return res
