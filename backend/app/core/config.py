from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "CHIQUISTRUKIS API"
    app_env: str = "development"
    app_debug: bool = True

    oracle_user: str = ""
    oracle_password: str = ""
    oracle_dsn: str = ""

    # Redis is external (infra/redis)
    redis_url: str = "redis://127.0.0.1:6379/0"

    access_token_expire_minutes: int = 720
    app_use_demo_store: bool = True
    app_allow_memory_session: bool = True

    support_files_dir: str = "storage/support_files"
    support_file_max_bytes: int = 5 * 1024 * 1024

    ai_enabled: bool = False
    ai_provider: str = ""
    ai_model: str = ""
    ai_min_confidence: float = 0.7
    openai_api_key: str = ""


settings = Settings()
