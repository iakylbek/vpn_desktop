"""
Model-слой.

Здесь только данные и их представление — никакой сетевой логики,
никакого Qt. Это то, чем оперируют ViewModel'и и что приходит
от backend'а (после разбора JSON).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ProfileStatus = Literal["inactive", "active", "error"]
ActionResult = Literal["success", "error"]
CoreMode = Literal["demo", "xray"]


@dataclass
class NetworkProfile:
    """Зеркало NetworkProfileRead на backend'е (app/schemas.py)."""

    id: int
    name: str
    host: str
    port: int
    protocol: str
    status: ProfileStatus
    description: str | None
    config: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "NetworkProfile":
        return NetworkProfile(
            id=data["id"],
            name=data["name"],
            host=data["host"],
            port=data["port"],
            protocol=data["protocol"],
            status=data["status"],
            description=data.get("description"),
            config=data.get("config", {}),
            created_at=_parse_dt(data.get("created_at")),
            updated_at=_parse_dt(data.get("updated_at")),
        )

    def to_create_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "description": self.description,
            "config": self.config,
        }


@dataclass
class RuntimeStatus:
    profile_id: int
    mode: CoreMode
    status: ProfileStatus
    running: bool
    pid: int | None
    message: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RuntimeStatus":
        return RuntimeStatus(
            profile_id=data["profile_id"],
            mode=data["mode"],
            status=data["status"],
            running=data["running"],
            pid=data.get("pid"),
            message=data["message"],
        )


@dataclass
class ValidationResult:
    profile_id: int
    mode: CoreMode
    valid: bool
    message: str
    config_path: str | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ValidationResult":
        return ValidationResult(
            profile_id=data["profile_id"],
            mode=data["mode"],
            valid=data["valid"],
            message=data["message"],
            config_path=data.get("config_path"),
        )


@dataclass
class ActionLogEntry:
    id: int
    profile_id: int | None
    action: str
    result: ActionResult
    message: str
    created_at: datetime | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ActionLogEntry":
        return ActionLogEntry(
            id=data["id"],
            profile_id=data.get("profile_id"),
            action=data["action"],
            result=data["result"],
            message=data["message"],
            created_at=_parse_dt(data.get("created_at")),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
