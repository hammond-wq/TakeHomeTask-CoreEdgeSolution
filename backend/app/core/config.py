from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    env: str = "dev"
    api_prefix: str = "/api"
    cors_origins: List[str] = ["http://localhost:5173"]
    database_url: str
    retell_api_key: str
    retell_base_url: str = "https://api.retellai.com"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)

settings = Settings()
