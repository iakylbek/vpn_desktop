"""
ViewModel формы создания/редактирования профиля.

Один класс обслуживает оба случая (create и edit): если profile is None —
это создание, иначе — редактирование существующего. Валидация полей
происходит здесь, а не в View, чтобы её можно было покрыть тестами
без запуска Qt-приложения.
"""
from __future__ import annotations

import json

from PySide6.QtCore import QObject, Signal

from app.models.profile import NetworkProfile
from app.services.api_client import ApiClient
from app.viewmodels.async_worker import run_async


class ProfileEditViewModel(QObject):
    saved = Signal(object)          # NetworkProfile — сохранение прошло успешно
    error_occurred = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, api: ApiClient, profile: NetworkProfile | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._api = api
        self._profile = profile
        self._workers = []

    @property
    def is_new(self) -> bool:
        return self._profile is None

    @property
    def profile(self) -> NetworkProfile | None:
        return self._profile

    def validate_fields(
        self, name: str, host: str, port_text: str, protocol: str, config_text: str
    ) -> tuple[dict | None, list[str]]:
        """Локальная (клиентская) проверка перед отправкой на backend.

        Возвращает (payload, errors). Если errors не пуст — payload будет None.
        """
        errors: list[str] = []

        name = name.strip()
        host = host.strip()
        protocol = protocol.strip()

        if not name:
            errors.append("Название профиля не может быть пустым")
        if not host:
            errors.append("Host не может быть пустым")
        if not protocol:
            errors.append("Protocol не может быть пустым")

        port: int | None = None
        try:
            port = int(port_text)
            if not (1 <= port <= 65535):
                errors.append("Port должен быть в диапазоне 1–65535")
        except ValueError:
            errors.append("Port должен быть целым числом")

        config: dict = {}
        config_text = config_text.strip()
        if config_text:
            try:
                config = json.loads(config_text)
                if not isinstance(config, dict):
                    errors.append("Config должен быть JSON-объектом ({...})")
            except json.JSONDecodeError as exc:
                errors.append(f"Config: невалидный JSON ({exc})")

        if errors:
            return None, errors

        return {
            "name": name,
            "host": host,
            "port": port,
            "protocol": protocol,
            "description": None,
            "config": config,
        }, []

    def save(self, payload: dict, description: str | None = None) -> None:
        payload = dict(payload)
        payload["description"] = description or None

        self.busy_changed.emit(True)
        if self.is_new:
            func, args = self._api.create_profile, (payload,)
        else:
            func, args = self._api.update_profile, (self._profile.id, payload)

        worker = run_async(func, *args, on_success=self._on_saved, on_error=self._on_error)
        self._workers.append(worker)

    def _on_saved(self, profile: NetworkProfile) -> None:
        self.busy_changed.emit(False)
        self._profile = profile
        self.saved.emit(profile)

    def _on_error(self, message: str) -> None:
        self.busy_changed.emit(False)
        self.error_occurred.emit(message)
