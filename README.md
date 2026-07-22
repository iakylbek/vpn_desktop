# Network Core Manager — desktop-клиент (MVVM, PySide6)
Реализует: список профилей, формы создания/редактирования,
подключение к backend API, отображение статусов/сообщений/ошибок.

## Архитектура (MVVM)

```
app/
  models/            Model — чистые dataclass'ы (NetworkProfile, RuntimeStatus, ...)
                      Зеркалят app/schemas.py backend'а. Ни requests, ни Qt здесь нет.

  services/
    api_client.py     Единственное место с HTTP-логикой (requests.Session).
                      Возвращает Model-объекты или бросает ApiError.

  viewmodels/
    async_worker.py               QThread-обёртка: любой вызов ApiClient уходит
                                  в фон, чтобы не подвешивать UI.
    profiles_list_viewmodel.py    Состояние и команды главного экрана
                                  (load/activate/deactivate/restart/delete/validate).
    profile_edit_viewmodel.py     Валидация полей формы + create/update.
    profile_details_viewmodel.py  Поллинг runtime-статуса и логов выбранного профиля.

    Правило: файлы в viewmodels/ не импортируют ничего из QtWidgets.
    Только QObject/Signal/QThread/QTimer — то, что не рисует UI.

  views/
    main_window.py          Главное окно: таблица профилей + тулбар + панель деталей.
    profile_form_dialog.py  Диалог создания/редактирования профиля.
    profiles_table_model.py QAbstractTableModel — техническая обёртка list[NetworkProfile]
                             для QTableView (это "M" в терминологии Qt, а не Model
                             всего приложения).

main.py    Точка входа, CLI-параметр --api-url.
```

Поток данных: **View** дёргает команду ViewModel → **ViewModel** просит
**Service (ApiClient)** сходить в сеть в фоновом `QThread` → результат
приходит сигналом обратно в ViewModel → ViewModel эмиттит сигнал
состояния → **View** перерисовывает то, что подписано на этот сигнал.
View никогда не вызывает `requests` напрямую, ViewModel никогда не
создаёт `QWidget`.

## Установка на Kali Linux

```bash
cd network_client
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Если каких-то Qt-библиотек не хватает на уровне системы (PySide6 тянет
свои бинарники, но иногда нужны системные X11-либы):

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0
```

## Запуск

Сначала backend:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export NETWORK_CORE_MODE=demo
fastapi dev app/main.py
```

Затем клиент:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
# или с другим адресом backend'а:
python main.py --api-url http://192.168.1.10:8000
```
