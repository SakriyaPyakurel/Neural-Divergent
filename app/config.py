from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import SecretStr
from pathlib import Path

ENV_FILE_PATH = Path(__file__).parent / ".env"

class Settings(BaseSettings):
    NEO4J_URL: str
    NEO4J_USER: str
    NEO4J_PASSWORD: SecretStr

    # API Security
    jwt_secret_key: SecretStr

    # Only loading from .env in development
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_file_encoding="utf-8")

# Loading settings once
settings = Settings()