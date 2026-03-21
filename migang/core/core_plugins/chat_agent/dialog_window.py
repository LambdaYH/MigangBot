from __future__ import annotations

import time
from dataclasses import dataclass

from nonebot.adapters.onebot.v11 import GroupMessageEvent


@dataclass(slots=True)
class DialogWindowState:
    expires_at: float
    source: str = "chat"
    refreshed_at: float = 0.0


class DialogWindowManager:
    def __init__(self) -> None:
        self._states: dict[str, DialogWindowState] = {}

    def _key(self, event: GroupMessageEvent) -> str:
        return f"group:{event.group_id}"

    def is_active(self, event: GroupMessageEvent) -> bool:
        key = self._key(event)
        state = self._states.get(key)
        if state and state.expires_at > time.time():
            return True
        self._states.pop(key, None)
        return False

    def refresh(
        self,
        event: GroupMessageEvent,
        window_minutes: int,
        source: str = "chat",
    ) -> None:
        now = time.time()
        self._states[self._key(event)] = DialogWindowState(
            expires_at=now + max(window_minutes, 1) * 60,
            source=source,
            refreshed_at=now,
        )

    def get_state(self, event: GroupMessageEvent) -> DialogWindowState | None:
        if not self.is_active(event):
            return None
        return self._states.get(self._key(event))

    def clear(self, event: GroupMessageEvent) -> None:
        self._states.pop(self._key(event), None)


dialog_window_manager = DialogWindowManager()
