class FileTypeError(Exception):
    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_

class FileParseError(Exception):
    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_

class ConfigNoExistError(Exception):
    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_