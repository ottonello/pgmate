"""Configuration management for PGMate."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """PostgreSQL database configuration."""

    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str = "public"

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None

    def __post_init__(self):
        """Set default model based on provider."""
        if self.model is None:
            if self.provider == "openai":
                self.model = "gpt-4"
            elif self.provider == "anthropic":
                self.model = "claude-3-5-sonnet-20241022"


@dataclass
class Config:
    """Main application configuration."""

    database: DatabaseConfig
    llm: LLMConfig
    memory_dir: Path

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables.

        Args:
            env_file: Path to .env file (optional)

        Returns:
            Config instance

        Raises:
            ValueError: If required configuration is missing
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Database configuration
        db_config = DatabaseConfig(
            host=os.getenv("PGMATE_DB_HOST", "localhost"),
            port=int(os.getenv("PGMATE_DB_PORT", "5432")),
            database=_get_required_env("PGMATE_DB_NAME"),
            user=_get_required_env("PGMATE_DB_USER"),
            password=_get_required_env("PGMATE_DB_PASSWORD"),
            schema=os.getenv("PGMATE_DB_SCHEMA", "public"),
        )

        # LLM configuration
        provider = os.getenv("PGMATE_LLM_PROVIDER", "openai").lower()

        if provider == "openai":
            api_key = _get_required_env("OPENAI_API_KEY")
            model = os.getenv("OPENAI_MODEL", "gpt-4")
        elif provider == "anthropic":
            api_key = _get_required_env("ANTHROPIC_API_KEY")
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        llm_config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
        )

        # Memory directory
        memory_dir_str = os.getenv("PGMATE_MEMORY_DIR", "~/.pgmate/memory")
        memory_dir = Path(memory_dir_str).expanduser()
        memory_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            database=db_config,
            llm=llm_config,
            memory_dir=memory_dir,
        )


def _get_required_env(key: str) -> str:
    """Get required environment variable.

    Args:
        key: Environment variable name

    Returns:
        Environment variable value

    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value
