from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app:app@db:5432/registry"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    admin_login: str = "admin"
    admin_password: str = "admin123"
    admin_department: str = "Администрация"
    mssql_conn: str = ""

    # Источник CSV (имитация MS SQL) и интервал автосинхронизации
    csv_source_path: str = "/app/data/fake_source.csv"
    sync_interval_hours: int = 6

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()