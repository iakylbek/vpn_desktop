from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.models.profile import RuntimeStatus
from app.services.api_client import ApiClient
from app.viewmodels.profile_details_viewmodel import ProfileDetailsViewModel
from app.viewmodels.profiles_list_viewmodel import ProfilesListViewModel
from app.views.profile_form_dialog import ProfileFormDialog
from app.views.profiles_table_model import ProfilesTableModel


class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient):
        super().__init__()
        self._api = api
        self.setWindowTitle("Network Core Manager — клиент")
        self.resize(1000, 620)

        self.list_vm = ProfilesListViewModel(api, parent=self)
        self.details_vm = ProfileDetailsViewModel(api, parent=self)

        self._table_model = ProfilesTableModel()
        self._build_ui()
        self._connect_viewmodels()

        self.list_vm.load_profiles()

    # -- построение UI ----------------------------------------------------------
    def _build_ui(self) -> None:
        toolbar = QToolBar("Действия")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._btn_new = QPushButton("Новый профиль")
        self._btn_edit = QPushButton("Изменить")
        self._btn_delete = QPushButton("Удалить")
        self._btn_validate = QPushButton("Проверить")
        self._btn_activate = QPushButton("Запустить")
        self._btn_deactivate = QPushButton("Остановить")
        self._btn_restart = QPushButton("Перезапустить")
        self._btn_refresh = QPushButton("Обновить список")

        for btn in [
            self._btn_new, self._btn_edit, self._btn_delete, self._btn_validate,
            self._btn_activate, self._btn_deactivate, self._btn_restart, self._btn_refresh,
        ]:
            toolbar.addWidget(btn)

        self._table = QTableView()
        self._table.setModel(self._table_model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        details_box = QGroupBox("Runtime-статус")
        self._runtime_label = QLabel("Профиль не выбран")
        self._runtime_label.setWordWrap(True)
        self._logs_view = QPlainTextEdit()
        self._logs_view.setReadOnly(True)
        self._logs_view.setPlaceholderText("Логи появятся здесь после выбора профиля...")
        details_layout = QVBoxLayout()
        details_layout.addWidget(self._runtime_label)
        details_layout.addWidget(QLabel("Последние строки лога:"))
        details_layout.addWidget(self._logs_view)
        details_box.setLayout(details_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._table)
        splitter.addWidget(details_box)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.setStatusBar(QStatusBar())
        self._set_action_buttons_enabled(False)

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_validate.clicked.connect(lambda: self._run_action(self.list_vm.validate_profile))
        self._btn_activate.clicked.connect(lambda: self._run_action(self.list_vm.activate_profile))
        self._btn_deactivate.clicked.connect(lambda: self._run_action(self.list_vm.deactivate_profile))
        self._btn_restart.clicked.connect(lambda: self._run_action(self.list_vm.restart_profile))
        self._btn_refresh.clicked.connect(self.list_vm.load_profiles)

    def _connect_viewmodels(self) -> None:
        self.list_vm.profiles_changed.connect(self._on_profiles_changed)
        self.list_vm.error_occurred.connect(self._show_error)
        self.list_vm.action_succeeded.connect(self._show_status)
        self.list_vm.busy_changed.connect(self._on_busy_changed)

        self.details_vm.runtime_changed.connect(self._on_runtime_changed)
        self.details_vm.logs_changed.connect(self._on_logs_changed)
        self.details_vm.error_occurred.connect(self._show_error)

    # -- обработчики сигналов ViewModel ------------------------------------------
    def _on_profiles_changed(self, profiles) -> None:
        selected_id = self._selected_profile_id()
        self._table_model.set_profiles(profiles)
        still_exists = selected_id is not None and any(p.id == selected_id for p in profiles)
        self._set_action_buttons_enabled(still_exists)
        if not still_exists:
            # Профиль, за которым следила панель деталей, больше не
            # существует (удалён/список обновился) — прекращаем опрос.
            self.details_vm.set_profile(None)

    def _on_runtime_changed(self, runtime: RuntimeStatus) -> None:
        pid_part = f", PID {runtime.pid}" if runtime.pid else ""
        self._runtime_label.setText(
            f"Профиль #{runtime.profile_id} · режим: {runtime.mode} · "
            f"статус: {runtime.status} · запущен: {'да' if runtime.running else 'нет'}{pid_part}\n"
            f"{runtime.message}"
        )

    def _on_logs_changed(self, lines: list[str]) -> None:
        self._logs_view.setPlainText("\n".join(lines))
        self._logs_view.verticalScrollBar().setValue(self._logs_view.verticalScrollBar().maximum())

    def _on_busy_changed(self, busy: bool) -> None:
        self.statusBar().showMessage("Загрузка..." if busy else "")

    def _show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Ошибка", message)

    # -- реакция на выбор строки -------------------------------------------------
    def _on_selection_changed(self, *_args) -> None:
        profile_id = self._selected_profile_id()
        self._set_action_buttons_enabled(profile_id is not None)
        self.details_vm.set_profile(profile_id)

    def _selected_profile_id(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        profile = self._table_model.profile_at(rows[0].row())
        return profile.id if profile else None

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        for btn in [
            self._btn_edit, self._btn_delete, self._btn_validate,
            self._btn_activate, self._btn_deactivate, self._btn_restart,
        ]:
            btn.setEnabled(enabled)

    # -- команды тулбара ----------------------------------------------------------
    def _on_new(self) -> None:
        dialog = ProfileFormDialog(self._api, profile=None, parent=self)
        if dialog.exec():
            self.list_vm.load_profiles()

    def _on_edit(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id is None:
            return
        profile = self.list_vm.profile_by_id(profile_id)
        dialog = ProfileFormDialog(self._api, profile=profile, parent=self)
        if dialog.exec():
            self.list_vm.load_profiles()

    def _on_delete(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id is None:
            return
        reply = QMessageBox.question(
            self, "Удаление профиля", f"Удалить профиль #{profile_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Останавливаем поллинг деталей сразу — иначе он ещё несколько
            # раз опросит уже удаляемый профиль и покажет лишние ошибки.
            self.details_vm.set_profile(None)
            self._table.clearSelection()
            self.list_vm.delete_profile(profile_id)

    def _run_action(self, command) -> None:
        profile_id = self._selected_profile_id()
        if profile_id is not None:
            command(profile_id)

    def closeEvent(self, event) -> None:
        self.details_vm.stop()
        super().closeEvent(event)
