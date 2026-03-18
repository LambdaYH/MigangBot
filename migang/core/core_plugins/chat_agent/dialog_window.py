from __future__ import annotations

import time

from nonebot.adapters.onebot.v11 import GroupMessageEvent


class DialogWindowManager:
    def __init__(self) -> None:
        self._expires_at: dict[str, float] = {}

    def _key(self, event: GroupMessageEvent) -> str:
        return f"group:{event.group_id}"

    def is_active(self, event: GroupMessageEvent) -> bool:
        key = self._key(event)
        expires_at = self._expires_at.get(key, 0)
        if expires_at > time.time():
            return True
        self._expires_at.pop(key, None)
        return False

    def refresh(self, event: GroupMessageEvent, window_minutes: int) -> None:
        self._expires_at[self._key(event)] = time.time() + max(window_minutes, 1) * 60

    def clear(self, event: GroupMessageEvent) -> None:
        self._expires_at.pop(self._key(event), None)


dialog_window_manager = DialogWindowManager()
