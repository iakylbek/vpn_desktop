"""
Точка входа desktop-клиента.

Запуск:
    python main.py
    python main.py --api-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.services.api_client import ApiClient
from app.views.main_window import MainWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Network Core Manager — desktop client")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Базовый URL backend API (по умолчанию http://127.0.0.1:8000)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Network Core Manager")

    api = ApiClient(base_url=args.api_url)
    if not api.check_health():
        QMessageBox.warning(
            None,
            "Backend недоступен",
            f"Не удалось подключиться к {args.api_url}.\n\n"
            "Убедитесь, что backend запущен:\n"
            "    fastapi dev app/main.py\n\n"
            "Приложение всё равно откроется — список профилей будет пуст,\n"
            "пока соединение не появится (кнопка «Обновить список»).",
        )

    window = MainWindow(api)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
