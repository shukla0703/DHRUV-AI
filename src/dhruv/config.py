from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from src.dhruv.theme import APP_NAME, DEFAULT_WAKE_WORD


load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    assistant_name: str = os.getenv("AETHER_NAME", APP_NAME)
    wake_word: str = os.getenv("AETHER_WAKE_WORD", DEFAULT_WAKE_WORD)
    auto_arm_wake_mode: bool = _env_bool("AETHER_AUTO_ARM_WAKE_MODE", True)
    start_minimized: bool = _env_bool("AETHER_START_MINIMIZED", False)
    llm_provider: str = os.getenv("AETHER_LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("AETHER_LLM_MODEL", "gpt-4o-mini")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    memory_turns: int = int(os.getenv("AETHER_MEMORY_TURNS", "6"))
    memory_store_path: str = os.getenv("AETHER_MEMORY_STORE", "data/dhruv_memory.json")
    memory_store_limit: int = int(os.getenv("AETHER_MEMORY_STORE_LIMIT", "200"))
    news_api_key: str = os.getenv("NEWS_API_KEY", "")
    opencage_api_key: str = os.getenv("OPENCAGE_API_KEY", "")
    default_browser: str = os.getenv("DEFAULT_BROWSER", "https://www.google.com")


settings = Settings()
