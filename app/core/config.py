from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Настройки приложения.
    """

    db_host: str = Field("localhost", validation_alias="DB_HOST")
    db_port: int = Field(5432, validation_alias="DB_PORT", ge=1, le=65535)
    db_name: str = Field("portfolio_db", validation_alias="DB_NAME")
    db_user: str = Field("portfolio_user", validation_alias="DB_USER")
    db_password: SecretStr = Field("portfolio_pass",
                                   validation_alias="DB_PASSWORD")

    # Путь к csv-файлу с текущими ценами акций
    prices_csv_path: str = Field(
        "data/Американские фондовые рынки.csv",
        validation_alias="PRICES_CSV_PATH",
        description="Путь к csv-файлу с ценами акций"
    )

    # Путь к json-файлу с маппингом тикеров на названия компаний
    ticker_map_path: str = Field(
        "data/ticker_map.json",
        validation_alias="TICKER_MAP_PATH",
        description="Путь к json-файлу с соответствием тикеров и названий компаний"
    )

    # Дополнительные настройки окружения
    environment: str = Field("development", validation_alias="ENVIRONMENT")
    debug: bool = Field(False, validation_alias="DEBUG")

    @property
    def database_url(self) -> str:
        """
        Формирует URL для подключения к БД.
        """
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password.get_secret_value()}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

settings = Settings()
