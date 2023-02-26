class FileTypeError(Exception):
    """文件类型错误"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_


class FileParseError(Exception):
    """文件解析错误"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_


class ConfigNoExistError(Exception):
    """配置文件不存在错误"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_


class SuspendShopHandler(Exception):
    """商品使用中断异常"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_
