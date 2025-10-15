from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    app_name: str = "ai-voice-agent-tool"
    environment: str = "dev"

    # Retell
    retell_base_url: str = Field(
        default="https://api.retellai.com",
        validation_alias=AliasChoices("RETELL_BASE_URL", "retell_base_url"),
    )
    retell_api_key: str = Field(validation_alias=AliasChoices("RETELL_API_KEY", "retell_api_key"))
    retell_webhook_secret: str = Field(default="", validation_alias=AliasChoices("RETELL_WEBHOOK_SECRET", "retell_webhook_secret"))
    retell_agent_id: str = Field(validation_alias=AliasChoices("RETELL_AGENT_ID", "retell_agent_id"))
    retell_agent_version: int = Field(default=1, validation_alias=AliasChoices("RETELL_AGENT_VERSION", "retell_agent_version"))

    # Supabase
    supabase_url: str = Field(validation_alias=AliasChoices("SUPABASE_URL", "supabase_url"))
    supabase_service_key: str = Field(validation_alias=AliasChoices("SUPABASE_SERVICE_KEY", "supabase_service_key"))

    # CORS
    cors_origins: str = Field(default="*", validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"))

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

settings = Settings()
