import contextlib

from nonebot import get_driver
from nonebot.permission import Permission
from nonebot.permission import SUPERUSER as NBSUPERUSER

from .depends import Session

SUPERUSER: Permission = NBSUPERUSER
"""匹配任意超级用户事件"""


def is_group_admin() -> Permission:
    permission = SUPERUSER

    # onebot11
    with contextlib.suppress(ImportError):
        from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

        permission = permission | GROUP_ADMIN | GROUP_OWNER

    return permission


GROUP_ADMIN = is_group_admin()


def is_group(session: Session) -> bool:
    return session.is_group


GROUP: Permission = Permission(is_group)
