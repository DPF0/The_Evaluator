import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class LLMConfig:
    """Configuration for the LLM backend."""
    provider: str = "local"  # "local" or "openai_compatible"
    base_url: str = "http://192.168.0.37:8084/v1"
    model: str = "unsloth/Qwen35"
    api_key: Optional[str] = None
    temperature: float = 0.2
    top_p: float = 0.5
    top_k: int = 10
    seed: int = 42
    max_tokens: int = 8000


@dataclass
class EmailConfig:
    """Configuration for Gmail SMTP."""
    enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""  # Use app password


@dataclass
class DatabaseConfig:
    """Configuration for SQLite database."""
    path: str = "data/evaluations.db"


@dataclass
class PathsConfig:
    """Configuration for file paths."""
    rubrics_dir: str = "rubrics"
    data_dir: str = "data"


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

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self)

    def save(self, path: str = "config.json") -> None:
        """Save config to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


def get_config() -> Config:
    """Get configuration, loading from file if available."""
    return Config.from_file()
