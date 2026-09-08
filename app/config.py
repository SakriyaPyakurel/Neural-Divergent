from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    neo4j_url: str
    neo4j_user: str
    neo4j_password: SecretStr

    # API Security
    jwt_secret_key: SecretStr

    # Only loading from .env in development
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Loading settings once
settings = Settings()