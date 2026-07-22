"""
View: диалог создания/редактирования профиля.

Диалог не ходит в сеть сам — он только собирает введённые пользователем
значения и передаёт их в ProfileEditViewModel.save(...). Результат
(успех/ошибка) диалог узнаёт через сигналы ViewModel'и.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.models.profile import NetworkProfile
from app.services.api_client import ApiClient
from app.viewmodels.profile_edit_viewmodel import ProfileEditViewModel


class ProfileFormDialog(QDialog):
    def __init__(self, api: ApiClient, profile: NetworkProfile | None = None, parent=None):
        super().__init__(parent)
        self.vm = ProfileEditViewModel(api, profile, parent=self)
        self.setWindowTitle("Новый профиль" if profile is None else f"Профиль #{profile.id}")
        self.setMinimumWidth(420)

        self._name = QLineEdit(profile.name if profile else "")
        self._host = QLineEdit(profile.host if profile else "")
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(profile.port if profile else 443)
        self._protocol = QLineEdit(profile.protocol if profile else "vless")
        self._description = QLineEdit(profile.description or "" if profile else "")

        import json
        config_text = json.dumps(profile.config, indent=2, ensure_ascii=False) if profile and profile.config else ""
        self._config = QPlainTextEdit(config_text)
        self._config.setPlaceholderText('{\n  "log": {"loglevel": "warning"},\n  "inbounds": [...],\n  "outbounds": [...]\n}')
        self._config.setMinimumHeight(140)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #c62828;")
        self._error_label.setWordWrap(True)
        self._error_label.hide()

        form = QFormLayout()
        form.addRow("Название:", self._name)
        form.addRow("Host:", self._host)
        form.addRow("Port:", self._port)
        form.addRow("Protocol:", self._protocol)
        form.addRow("Описание:", self._description)
        form.addRow("Config (JSON):", self._config)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_save_clicked)
        buttons.rejected.connect(self.reject)
        self._buttons = buttons

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error_label)
        layout.addWidget(buttons)

        self.vm.saved.connect(self._on_saved)
        self.vm.error_occurred.connect(self._on_error)
        self.vm.busy_changed.connect(lambda busy: buttons.setEnabled(not busy))

    def _on_save_clicked(self) -> None:
        payload, errors = self.vm.validate_fields(
            name=self._name.text(),
            host=self._host.text(),
            port_text=str(self._port.value()),
            protocol=self._protocol.text(),
            config_text=self._config.toPlainText(),
        )
        if errors:
            self._show_error("\n".join(errors))
            return
        self._error_label.hide()
        self.vm.save(payload, description=self._description.text().strip() or None)

    def _on_saved(self, _profile) -> None:
        self.accept()

    def _on_error(self, message: str) -> None:
        self._show_error(f"Backend отклонил запрос: {message}")

    def _show_error(self, text: str) -> None:
        self._error_label.setText(text)
        self._error_label.show()
