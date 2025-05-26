from langchain_core.tools import tool


@tool
def text_transform(text: str, transform_type: str = "upper") -> str:
    """文本转换工具，支持upper、lower、title、reverse"""
    transforms = {
        "upper": lambda x: x.upper(),
        "lower": lambda x: x.lower(),
        "title": lambda x: x.title(),
        "reverse": lambda x: x[::-1],
    }
    if transform_type not in transforms:
        return f"不支持的转换类型: {transform_type}，支持的类型: {', '.join(transforms.keys())}"
    try:
        result = transforms[transform_type](text)
        return f"转换结果({transform_type}): {result}"
    except Exception as e:
        return f"转换错误: {str(e)}"
