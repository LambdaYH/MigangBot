class BreakSession(Exception):
    """强制中断会话"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_
