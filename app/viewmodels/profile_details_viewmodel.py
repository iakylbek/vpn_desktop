from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from app.models.profile import RuntimeStatus
from app.services.api_client import ApiClient
from app.viewmodels.async_worker import run_async

POLL_INTERVAL_MS = 3000


class ProfileDetailsViewModel(QObject):
    runtime_changed = Signal(object)   # RuntimeStatus
    logs_changed = Signal(list)        # list[str]
    error_occurred = Signal(str)

    def __init__(self, api: ApiClient, parent: QObject | None = None):
        super().__init__(parent)
        self._api = api
        self._profile_id: int | None = None
        self._workers = []

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

    def set_profile(self, profile_id: int | None) -> None:
        self._profile_id = profile_id
        if profile_id is None:
            self._timer.stop()
            return
        self._poll()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        if self._profile_id is None:
            return
        pid = self._profile_id
        w1 = run_async(self._api.get_runtime, pid, on_success=self._on_runtime, on_error=self._on_poll_error)
        w2 = run_async(self._api.get_logs, pid, 200, on_success=self.logs_changed.emit, on_error=self._on_poll_error)
        self._workers.extend([w1, w2])

    def _on_runtime(self, runtime: RuntimeStatus) -> None:
        self.runtime_changed.emit(runtime)

    def _on_poll_error(self, message: str) -> None:
        # Профиль мог быть удалён/деактивирован параллельно с опросом.
        # Останавливаем поллинг сразу, чтобы не показывать одну и ту же
        # ошибку раз в 3 секунды бесконечно — она уже не актуальна для
        # текущего выбора пользователя.
        if self._timer.isActive():
            self._timer.stop()
            self.error_occurred.emit(message)
