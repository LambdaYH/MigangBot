from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Union, TypeVar

import anyio
import ujson as json
from ruamel.yaml import YAML, CommentedMap
from ruamel.yaml.scanner import ScannerError

_yaml = YAML(typ="rt")
_file_suffixes = [".json", ".yaml", ".yml"]
T = TypeVar("T")


def load_data(file: Union[Path, str]) -> Union[Dict, CommentedMap, List]:
    data: Union[Dict, CommentedMap, List, None] = None
    if isinstance(file, str):
        file = Path(file)
    if file.suffix not in _file_suffixes:
        raise Exception("路径必须为json或yaml格式的文件")
    if file.exists():
        with open(file, "r", encoding="utf-8") as f:
            if file.suffix == ".json":
                try:
                    data = json.load(f)
                except ValueError as e:
                    raise Exception(f"json文件 {file} 解析失败：{e}")
            else:
                try:
                    data = _yaml.load(f)
                except ScannerError as e:
                    raise Exception(f"yaml文件 {file} 解析失败：{e}")
    if data is None:
        return {} if file.suffix == ".json" else CommentedMap()
    return data


async def async_load_data(file: Union[Path, str]) -> Union[Dict, CommentedMap, List]:
    data: Union[Dict, CommentedMap, List, None] = None
    if isinstance(file, str):
        file = Path(file)
    if file.suffix not in _file_suffixes:
        raise Exception("路径必须为json或yaml格式的文件")
    if file.exists():
        async with await anyio.open_file(file, "r", encoding="utf-8") as f:
            data_str = await f.read()
            if file.suffix == ".json":
                try:
                    data = json.loads(data_str)
                except ValueError as e:
                    raise Exception(f"json文件 {file} 解析失败：{e}")
            else:
                try:
                    data = _yaml.load(data_str)
                except ScannerError as e:
                    raise Exception(f"yaml文件 {file} 解析失败：{e}")
    if data is None:
        return {} if file.suffix == ".json" else CommentedMap()
    return data
