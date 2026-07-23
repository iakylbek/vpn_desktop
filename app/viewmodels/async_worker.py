from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal


class _WorkerSignals(QObject):
    finished = Signal(object)   # результат: любой Model-объект/список
    failed = Signal(str)        # текст ошибки (ApiError.message или иное)


class ApiWorker(QThread):
    """Выполняет один вызов func(*args, **kwargs) в отдельном потоке."""

    def __init__(self, func: Callable[..., Any], *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            result = self._func(*self._args, **self._kwargs)
        except Exception as exc:  # ApiError и что угодно неожиданное
            self.signals.failed.emit(str(exc))
        else:
            self.signals.finished.emit(result)


def run_async(
    func: Callable[..., Any],
    *args,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    owner: QObject | None = None,
    **kwargs,
) -> ApiWorker:
    """
    Запускает func в фоне и возвращает сам ApiWorker.

    Вызывающий код ДОЛЖЕН удержать ссылку на возвращённый worker
    (например self._workers.append(worker)), иначе Python/Qt может
    удалить объект до завершения потока.
    """
    worker = ApiWorker(func, *args, **kwargs)
    if on_success:
        worker.signals.finished.connect(on_success)
    if on_error:
        worker.signals.failed.connect(on_error)
    # чистим поток после завершения, чтобы не копились объекты
    worker.finished.connect(worker.deleteLater)
    worker.start()
    return worker
