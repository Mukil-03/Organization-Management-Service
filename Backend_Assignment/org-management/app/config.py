from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URI")
    master_db_name: str = Field(default="org_master", alias="MASTER_DB_NAME")
    secret_key: str = Field(default="changeme", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


