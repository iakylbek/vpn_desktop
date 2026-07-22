"""
ViewModel для главного экрана — списка сетевых профилей.

Правило MVVM, которое здесь важно соблюсти: ViewModel не импортирует
ничего из QtWidgets и не знает, что где-то есть QTableView или QDialog.
Он выставляет наружу:
  - свойства/сигналы состояния (profiles_changed, error, busy_changed);
  - команды (load_profiles, activate, deactivate, delete, ...).
View просто подписывается на сигналы и дёргает команды.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.models.profile import NetworkProfile
from app.services.api_client import ApiClient
from app.viewmodels.async_worker import run_async


class ProfilesListViewModel(QObject):
    profiles_changed = Signal(list)     # list[NetworkProfile]
    error_occurred = Signal(str)
    busy_changed = Signal(bool)
    action_succeeded = Signal(str)       # текст для статус-бара

    def __init__(self, api: ApiClient, parent: QObject | None = None):
        super().__init__(parent)
        self._api = api
        self._profiles: list[NetworkProfile] = []
        self._workers = []  # держим ссылки, чтобы QThread не собрался раньше времени

    # -- свойство только для чтения из View ----------------------------------
    @property
    def profiles(self) -> list[NetworkProfile]:
        return self._profiles

    def profile_by_id(self, profile_id: int) -> NetworkProfile | None:
        return next((p for p in self._profiles if p.id == profile_id), None)

    # -- команды --------------------------------------------------------------
    def load_profiles(self) -> None:
        self._run(self._api.list_profiles, on_success=self._on_profiles_loaded)

    def delete_profile(self, profile_id: int) -> None:
        self._run(
            self._api.delete_profile,
            profile_id,
            on_success=lambda _=None: self._after_action(f"Профиль #{profile_id} удалён"),
        )

    def validate_profile(self, profile_id: int) -> None:
        self._run(
            self._api.validate_profile,
            profile_id,
            on_success=lambda r: self._after_action(
                f"Валидация #{profile_id}: {'OK' if r.valid else 'ошибка'} — {r.message}"
            ),
        )

    def activate_profile(self, profile_id: int) -> None:
        self._run(
            self._api.activate_profile,
            profile_id,
            on_success=lambda _=None: self._after_action(f"Профиль #{profile_id} запущен"),
        )

    def deactivate_profile(self, profile_id: int) -> None:
        self._run(
            self._api.deactivate_profile,
            profile_id,
            on_success=lambda _=None: self._after_action(f"Профиль #{profile_id} остановлен"),
        )

    def restart_profile(self, profile_id: int) -> None:
        self._run(
            self._api.restart_profile,
            profile_id,
            on_success=lambda _=None: self._after_action(f"Профиль #{profile_id} перезапущен"),
        )

    # -- внутреннее -------------------------------------------------------------
    def _after_action(self, message: str) -> None:
        self.action_succeeded.emit(message)
        self.load_profiles()  # обновляем список/статусы после любого действия

    def _on_profiles_loaded(self, profiles: list[NetworkProfile]) -> None:
        self._profiles = profiles
        self.profiles_changed.emit(profiles)

    def _run(self, func, *args, on_success) -> None:
        self.busy_changed.emit(True)

        def _wrapped_success(result):
            self.busy_changed.emit(False)
            on_success(result)

        def _wrapped_error(message: str):
            self.busy_changed.emit(False)
            self.error_occurred.emit(message)

        worker = run_async(func, *args, on_success=_wrapped_success, on_error=_wrapped_error)
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
