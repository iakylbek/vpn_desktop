"""
QAbstractTableModel — это "M" в терминологии самого Qt, но в нашей
MVVM-архитектуре он живёт внутри View-слоя: это чисто техническая
обёртка, которая знает, как показать list[NetworkProfile] в QTableView.
Бизнес-логику (когда грузить, что делать при ошибке и т.д.) он не содержит —
это уже отвечает ProfilesListViewModel.
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.models.profile import NetworkProfile

COLUMNS = ["ID", "Название", "Host", "Port", "Protocol", "Статус"]

STATUS_LABELS = {
    "inactive": "Неактивен",
    "active": "Активен",
    "error": "Ошибка",
}


class ProfilesTableModel(QAbstractTableModel):
    def __init__(self, profiles: list[NetworkProfile] | None = None):
        super().__init__()
        self._profiles: list[NetworkProfile] = profiles or []

    def set_profiles(self, profiles: list[NetworkProfile]) -> None:
        self.beginResetModel()
        self._profiles = profiles
        self.endResetModel()

    def profile_at(self, row: int) -> NetworkProfile | None:
        if 0 <= row < len(self._profiles):
            return self._profiles[row]
        return None

    # -- обязательные переопределения QAbstractTableModel ---------------------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._profiles)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        profile = self._profiles[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return [
                profile.id,
                profile.name,
                profile.host,
                profile.port,
                profile.protocol,
                STATUS_LABELS.get(profile.status, profile.status),
            ][col]

        if role == Qt.ItemDataRole.ForegroundRole and col == 5:
            from PySide6.QtGui import QColor
            return {
                "active": QColor("#2e7d32"),
                "error": QColor("#c62828"),
                "inactive": QColor("#616161"),
            }.get(profile.status)

        return None
