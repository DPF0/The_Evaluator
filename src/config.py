import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

ENV_PREFIX = "EVALUATOR_"


@dataclass
class LLMConfig:
    """Configuration for the LLM backend."""
    provider: str = "local"
    base_url: str = "http://192.168.0.37:8084/v1"
    model: str = "unsloth/Qwen35"
    api_key: Optional[str] = None
    temperature: float = 0.2
    top_p: float = 0.5
    top_k: int = 10
    seed: int = 42
    max_tokens: int = 8000

    ENV_KEYS = {
        "provider": "LLM_PROVIDER",
        "base_url": "LLM_BASE_URL",
        "model": "LLM_MODEL",
        "api_key": "LLM_API_KEY",
        "temperature": "LLM_TEMPERATURE",
        "top_p": "LLM_TOP_P",
        "top_k": "LLM_TOP_K",
        "seed": "LLM_SEED",
        "max_tokens": "LLM_MAX_TOKENS",
    }


@dataclass
class EmailConfig:
    """Configuration for Gmail SMTP."""
    enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""

    ENV_KEYS = {
        "enabled": "EMAIL_ENABLED",
        "smtp_server": "EMAIL_SMTP_SERVER",
        "smtp_port": "EMAIL_SMTP_PORT",
        "sender_email": "EMAIL_SENDER",
        "sender_password": "EMAIL_PASSWORD",
    }


@dataclass
class DatabaseConfig:
    """Configuration for SQLite database."""
    path: str = "data/evaluations.db"

    ENV_KEYS = {
        "path": "DATABASE_PATH",
    }


@dataclass
class PathsConfig:
    """Configuration for file paths."""
    rubrics_dir: str = "rubrics"
    data_dir: str = "data"

    ENV_KEYS = {
        "rubrics_dir": "RUBRICS_DIR",
        "data_dir": "DATA_DIR",
    }


def _apply_env(obj: object) -> object:
    """Override object fields from environment variables."""
    env_keys = getattr(obj, "ENV_KEYS", {})
    for attr, env_key in env_keys.items():
        raw = os.environ.get(f"{ENV_PREFIX}{env_key}")
        if raw is not None:
            current = getattr(obj, attr)
            if isinstance(current, bool):
                val = raw.lower() in ("true", "1", "yes")
            elif isinstance(current, int):
                val = int(raw)
            elif isinstance(current, float):
                val = float(raw)
            else:
                val = raw
            setattr(obj, attr, val)
    return obj


@dataclass
class Config:
    """Main configuration class."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    @classmethod
    def from_file(cls, path: str = "config.json") -> "Config":
        """Load config from JSON file."""
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            llm_data = data.get("llm", {})
            email_data = data.get("email", {})
            db_data = data.get("database", {})
            paths_data = data.get("paths", {})
            return cls(
                llm=LLMConfig(**llm_data),
                email=EmailConfig(**email_data),
                database=DatabaseConfig(**db_data),
                paths=PathsConfig(**paths_data),
            )
        return cls()

    @classmethod
    def load(cls, path: str = "config.json") -> "Config":
        """Load config with priority: env vars > config.json > defaults."""
        config = cls.from_file(path)
        _apply_env(config.llm)
        _apply_env(config.email)
        _apply_env(config.database)
        _apply_env(config.paths)
        return config

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)

    def save(self, path: str = "config.json") -> None:
        """Save config to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


def get_config() -> Config:
    """Get configuration with priority: env vars > config.json > defaults."""
    return Config.load()
