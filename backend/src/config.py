"""
Stock Analysis Agent - Main Configuration
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Browserbase settings
    browserbase_api_key: str = ""
    browserbase_project_id: str = ""

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-r1:8b"

    # Data source URLs
    yahoo_finance_base_url: str = "https://finance.yahoo.com"
    google_finance_base_url: str = "https://www.google.com/finance"

    # Directory settings
    reports_dir: Path = Path("./reports")
    temp_dir: Path = Path("./temp")
    logs_dir: Path = Path("./logs")

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/agent.log"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "forbid"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        for directory in [
            self.reports_dir,
            self.temp_dir,
            self.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
