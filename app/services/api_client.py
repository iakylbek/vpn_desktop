"""
Service-слой (иногда его выделяют отдельно от Model в MVVM).

ApiClient — единственный модуль в приложении, который знает про HTTP
и про адреса backend'а. ViewModel'и вызывают его методы и получают
либо готовые Model-объекты, либо ApiError.

Это соответствует пункту 6 индивидуального задания:
"Настроить взаимодействие клиентской части с backend API".
"""
from __future__ import annotations

import requests

from app.models.profile import (
    ActionLogEntry,
    NetworkProfile,
    RuntimeStatus,
    ValidationResult,
)


class ApiError(Exception):
    """Единая ошибка для View/ViewModel: сеть, таймаут, HTTP 4xx/5xx."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # -- внутренний помощник -------------------------------------------------
    def _request(self, method: str, path: str, **kwargs) -> dict | list | None:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.ConnectionError as exc:
            raise ApiError(f"Нет соединения с backend'ом ({url})") from exc
        except requests.Timeout as exc:
            raise ApiError("Backend не отвечает (timeout)") from exc
        except requests.RequestException as exc:
            raise ApiError(f"Ошибка запроса: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_detail(response)
            raise ApiError(detail, status_code=response.status_code)

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # -- health ---------------------------------------------------------------
    def check_health(self) -> bool:
        try:
            self._request("GET", "/health")
            return True
        except ApiError:
            return False

    # -- профили ----------------------------------------------------------------
    def list_profiles(self) -> list[NetworkProfile]:
        data = self._request("GET", "/api/profiles") or []
        return [NetworkProfile.from_dict(item) for item in data]

    def get_profile(self, profile_id: int) -> NetworkProfile:
        data = self._request("GET", f"/api/profiles/{profile_id}")
        return NetworkProfile.from_dict(data)

    def create_profile(self, payload: dict) -> NetworkProfile:
        data = self._request("POST", "/api/profiles", json=payload)
        return NetworkProfile.from_dict(data)

    def update_profile(self, profile_id: int, payload: dict) -> NetworkProfile:
        data = self._request("PATCH", f"/api/profiles/{profile_id}", json=payload)
        return NetworkProfile.from_dict(data)

    def delete_profile(self, profile_id: int) -> None:
        self._request("DELETE", f"/api/profiles/{profile_id}")

    # -- управление ядром -------------------------------------------------------
    def validate_profile(self, profile_id: int) -> ValidationResult:
        data = self._request("POST", f"/api/profiles/{profile_id}/validate")
        return ValidationResult.from_dict(data)

    def activate_profile(self, profile_id: int) -> NetworkProfile:
        data = self._request("POST", f"/api/profiles/{profile_id}/activate")
        return NetworkProfile.from_dict(data)

    def deactivate_profile(self, profile_id: int) -> NetworkProfile:
        data = self._request("POST", f"/api/profiles/{profile_id}/deactivate")
        return NetworkProfile.from_dict(data)

    def restart_profile(self, profile_id: int) -> NetworkProfile:
        data = self._request("POST", f"/api/profiles/{profile_id}/restart")
        return NetworkProfile.from_dict(data)

    def get_runtime(self, profile_id: int) -> RuntimeStatus:
        data = self._request("GET", f"/api/profiles/{profile_id}/runtime")
        return RuntimeStatus.from_dict(data)

    def get_logs(self, profile_id: int, lines: int = 200) -> list[str]:
        data = self._request("GET", f"/api/profiles/{profile_id}/logs", params={"lines": lines})
        return data["lines"]

    # -- журнал действий ---------------------------------------------------------
    def list_actions(self, profile_id: int | None = None, limit: int = 100) -> list[ActionLogEntry]:
        params = {"limit": limit}
        if profile_id is not None:
            params["profile_id"] = profile_id
        data = self._request("GET", "/api/actions", params=params) or []
        return [ActionLogEntry.from_dict(item) for item in data]


def _extract_detail(response: requests.Response) -> str:
    try:
        body = response.json()
        return str(body.get("detail", response.text))
    except ValueError:
        return response.text or f"HTTP {response.status_code}"
