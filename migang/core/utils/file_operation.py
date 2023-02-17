from io import StringIO
from pathlib import Path
from typing import TypeVar, Union, Dict, Any, List

import anyio
import ujson as json
from ruamel.yaml import CommentedMap
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

from migang.core.exception import FileTypeError, FileParseError

_yaml = YAML(typ="rt")
_file_suffixes = [".json", ".yaml", ".yml"]
T = TypeVar("T")


def load_data(file: Union[Path, str]) -> Union[Dict, CommentedMap, List]:
    """同步加载.json或.yaml数据

    Args:
        file (Union[Path, str]): 文件路径

    Raises:
        FileTypeError: 文件类型错误
        FileParseError: 文件解析失败

    Returns:
        Union[Dict, CommentedMap, List]: 若json返回Dict或List，若yaml返回CommentedMap
    """
    data: Union[Dict, CommentedMap, List, None] = None
    if isinstance(file, str):
        file = Path(file)
    if file.suffix not in _file_suffixes:
        raise FileTypeError("路径必须为json或yaml格式的文件")
    if file.exists():
        with open(file, "r", encoding="utf-8") as f:
            if file.suffix == ".json":
                try:
                    data = json.load(f)
                except ValueError as e:
                    raise FileParseError(f"json文件 {file} 解析失败：{e}")
            else:
                try:
                    data = _yaml.load(f)
                except ScannerError as e:
                    raise FileParseError(f"yaml文件 {file} 解析失败：{e}")
    if data is None:
        return {} if file.suffix == ".json" else CommentedMap()
    return data


def save_data(
    obj: Union[Dict[str, Any], List[Any], CommentedMap], file: Union[Path, str]
) -> None:
    """同步保存数据

    Args:
        obj (Union[Dict[str, Any], CommentedMap]): 对象
        file (Union[Path, str]): 文件路径
    """
    if isinstance(file, str):
        file = Path(file)
    file.parent.mkdir(exist_ok=True, parents=True)
    with open(file, "w", encoding="utf-8") as f:
        if file.suffix == ".json":
            json.dump(obj, f, ensure_ascii=False, indent=4)
        else:
            _yaml.dump(obj, f)


async def async_load_data(file: Union[Path, str]) -> Union[Dict, CommentedMap, List]:
    """异步加载.json或.yaml数据

    Args:
        file (Union[Path, str]): 文件路径

    Raises:
        FileTypeError: 文件类型错误
        FileParseError: 文件解析失败

    Returns:
        Union[Dict, CommentedMap, List]: 若json返回Dict或List，若yaml返回CommentedMap
    """
    data: Union[Dict, CommentedMap, List, None] = None
    if isinstance(file, str):
        file = Path(file)
    if file.suffix not in _file_suffixes:
        raise FileTypeError("路径必须为json或yaml格式的文件")
    if file.exists():
        async with await anyio.open_file(file, "r", encoding="utf-8") as f:
            data_str = await f.read()
            if file.suffix == ".json":
                try:
                    data = json.loads(data_str)
                except ValueError as e:
                    raise FileParseError(f"json文件 {file} 解析失败：{e}")
            else:
                try:
                    data = _yaml.load(data_str)
                except ScannerError as e:
                    raise FileParseError(f"yaml文件 {file} 解析失败：{e}")
    if data is None:
        return {} if file.suffix == ".json" else CommentedMap()
    return data


async def async_save_data(
    obj: Union[Dict[str, Any], List[Any], CommentedMap], file: Union[Path, str]
) -> None:
    """异步保存数据

    Args:
        obj (Union[Dict[str, Any], List[Any], CommentedMap]): 对象
        file (Union[Path, str]): 文件路径
    """
    if isinstance(file, str):
        file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    async with await anyio.open_file(file, "w", encoding="utf-8") as f:
        if file.suffix == ".json":
            await f.write(json.dumps(obj, ensure_ascii=False, indent=4))
        else:
            with StringIO() as data:
                _yaml.dump(obj, data)
                await f.write(data.getvalue())
