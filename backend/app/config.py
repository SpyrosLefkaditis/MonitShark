"""Application configuration. Loads from env + config/port.yml + config/users.yml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Required (defaults make local dev easy; production must set these)
    groq_api_key: str = ""
    jwt_secret: str = "dev-only-replace-me-please"

    # Paths
    host_root: str = "/host"
    data_dir: str = "/data"
    config_dir: str = "/config"
    config_example_dir: str = "/config.example"

    # Bind (defaults; overridden by config/port.yml at runtime if present)
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000

    # JWT
    jwt_alg: str = "HS256"
    jwt_lifetime_s: int = 60 * 60 * 24

    # Logging
    log_level: str = "info"

    @property
    def port_yaml_path(self) -> Path:
        return Path(self.config_dir) / "port.yml"

    @property
    def users_yaml_path(self) -> Path:
        return Path(self.config_dir) / "users.yml"


settings = Settings()


@dataclass
class PortConfig:
    http: int
    https: int
    bind_host: str
    bind_port: int


def load_port_config() -> PortConfig:
    """Read config/port.yml. Returns sensible defaults if missing or partial."""
    p = settings.port_yaml_path
    if not p.exists():
        return PortConfig(
            http=80, https=443,
            bind_host=settings.bind_host, bind_port=settings.bind_port,
        )
    data: dict[str, Any] = yaml.safe_load(p.read_text()) or {}
    ports = data.get("ports") or {}
    backend = data.get("backend") or {}
    return PortConfig(
        http=int(ports.get("http", 80)),
        https=int(ports.get("https", 443)),
        bind_host=str(backend.get("bind_host", settings.bind_host)),
        bind_port=int(backend.get("bind_port", settings.bind_port)),
    )
