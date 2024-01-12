from nonebot.adapters import Bot, Event
from nonebot_plugin_session import Session, SessionLevel, SessionIdType, extract_session


class MigangSession:
    """session，跨平台"""

    def __init__(self, session: Session) -> None:
        self.__session = session
        self.__user_id: str = self.__session.get_id(
            SessionIdType.USER,
            include_platform=False,
            include_bot_type=False,
            include_bot_id=False,
        )
        self.__is_group: bool = self.__session.level > SessionLevel.LEVEL1
        self.__group_id: str = (
            self.__session.get_id(
                SessionIdType.GROUP,
                include_platform=False,
                include_bot_type=False,
                include_bot_id=False,
            )
            if self.__is_group
            else None
        )

        self.__has_user: bool = self.__user_id != ""
        self.__platform: str = self.__session.platform

    @staticmethod
    def get_session(bot: Bot, event: Event):
        return MigangSession(extract_session(bot=bot, event=event))

    @property
    def user_id(self) -> str:
        return self.__user_id

    @property
    def group_id(self) -> str:
        return self.__group_id

    @property
    def is_group(self) -> bool:
        return self.__is_group

    @property
    def has_user(self) -> bool:
        return self.__has_user

    @property
    def platform(self) -> str:
        return self.__platform
