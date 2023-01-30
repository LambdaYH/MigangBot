from io import StringIO
from pathlib import Path
from typing import TypeVar, Union, Dict, Any

import aiofiles
import ujson as json
from ruamel.yaml import YAML

from migangbot.core.exception import FileTypeError, FileParseError

_yaml = YAML(typ="safe")
_file_suffixes = [".json", ".yaml", ".yml"]
T = TypeVar("T")


def LoadData(file: Union[Path, str]):
    data: Dict = {}
    if isinstance(file, str):
        file = Path(file)
    if file.suffix not in _file_suffixes:
        raise FileTypeError("路径必须为json或yaml格式的文件")
    file.parent.mkdir(exist_ok=True, parents=True)
    if file.exists():
        with open(file, "r", encoding="utf-8") as f:
            if file.suffix == ".json":
                try:
                    data = json.load(f)
                except ValueError as e:
                    raise FileParseError(f"文件解析失败：{e}")
            else:
                data = _yaml.load(f)
    return data


def SaveData(obj: Dict[str, Any], file: Union[Path, str]):
    if isinstance(file, str):
        file = Path(file)
    with open(file, "w", encoding="utf-8") as f:
        if file.suffix == ".json":
            json.dump(obj, f, ensure_ascii=False, indent=4)
        else:
            _yaml.dump(obj, f, indent=2, allow_unicode=True)


async def AsyncLoadData(file: Union[Path, str]):
    data: Dict = {}
    if isinstance(file, str):
        file = Path(file)
    if file.suffix not in _file_suffixes:
        raise FileTypeError("路径必须为json或yaml格式的文件")
    file.parent.mkdir(exist_ok=True, parents=True)
    if file.exists():
        async with aiofiles.open(file, "r", encoding="utf-8") as f:
            data_str = await f.read()
            if file.suffix == ".json":
                try:
                    data = json.loads(data_str)
                except ValueError as e:
                    raise FileParseError(f"文件解析失败：{e}")
            else:
                data = _yaml.load(StringIO(data_str))
    return data


async def AsyncSaveData(obj: Dict[str, Any], file: Union[Path, str]):
    if isinstance(file, str):
        file = Path(file)
    async with aiofiles.open(file, "w", encoding="utf-8") as f:
        if file.suffix == ".json":
            await f.write(json.dumps(obj, ensure_ascii=False, indent=4))
        else:
            with StringIO() as data:
                _yaml.dump(obj, data, indent=2, allow_unicode=True)
                await f.write(data.getvalue())
