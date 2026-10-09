"""
Application settings
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from dotenv import load_dotenv

def init_settings():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    print("ENV loaded")

class Settings(BaseSettings):
    """Application settings (env + defaults)"""

    # Pydantic Settings Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # ------------------------------------------------------------------
    # APP / ENVIRONMENT
    # ------------------------------------------------------------------
    app_name: str = Field(default="NoCode Backend", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
    # Tam URL kullanıyoruz; no-code projelerde bu değer AI / generator tarafından yazılacak.
    async_database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/app_db",
        alias="ASYNC_DATABASE_URL",
    )
    sync_database_url: Optional[str] = Field(
        default=None,
        alias="SYNC_DATABASE_URL",
        description="Optional sync DB URL (Alembic için). Eğer None ise async URL'den türetilebilir.",
    )

    # ------------------------------------------------------------------
    # JWT CONFIGURATION (auth/jwt.py ile uyumlu)
    # ------------------------------------------------------------------
    secret_key: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        alias="JWT_SECRET",
    )
    refresh_secret_key: str = Field(
        default="your-super-secret-refresh-key-change-in-production",
        alias="JWT_REFRESH_SECRET",
    )
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_EXPIRE_MIN")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_EXPIRE_DAYS")

    jwt_issuer: Optional[str] = Field(default=None, alias="JWT_ISSUER")
    jwt_audience: Optional[str] = Field(default=None, alias="JWT_AUDIENCE")

    # ------------------------------------------------------------------
    # PASSWORD HASHING
    # ------------------------------------------------------------------
    password_hash_algorithm: str = Field(
        default="bcrypt", alias="HASH_SCHEME"  # veya "argon2"
    )
    bcrypt_rounds: int = Field(default=12, alias="BCRYPT_ROUNDS")

    # Argon2 için ek ayarlar (istersen kullanırsın)
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 65536  # 64 MB
    argon2_parallelism: int = 1

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            f"http://localhost:{port}" for port in range(10000, 11000)
        ],
        alias="CORS_ORIGINS",
        description=(
            "Comma-separated veya JSON array olarak .env'den gelebilir. "
            "Frontend 10000-10999 arası dinamik port alabilir."
        ),
    )

    # ------------------------------------------------------------------
    # SERVER
    # ------------------------------------------------------------------
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = Field(default=True, alias="RELOAD")
    access_log: bool = Field(default=True, alias="ACCESS_LOG")

    # ------------------------------------------------------------------
    # SMTP / EMAIL
    # ------------------------------------------------------------------
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="", alias="SMTP_FROM_NAME")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")

   

    # ------------------------------------------------------------------
    # VALIDATORS
    # ------------------------------------------------------------------

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """DEBUG env'ini string/bool fark etmeksizin bool'a çevir."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        CORS_ORIGINS env'i:
        - JSON array: '["http://a.com","http://b.com"]'
        - veya comma-separated: "http://a.com,http://b.com"
        şeklinde gelebilir. Her iki durumu da destekle.
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # JSON array gibi görünüyorsa Pydantic zaten parse eder,
            # ama biz yine de virgül ile split etmeyi destekleyelim.
            if v.strip().startswith("[") and v.strip().endswith("]"):
                # Pydantic bunu otomatik çözeceği için aynen bırak
                return v
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # ------------------------------------------------------------------
    # HELPER PROPERTIES / METHODS
    # ------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        """Prod modda mıyız? (debug False ise prod kabul ediyoruz)"""
        return not self.debug

    def get_jwt_settings(self) -> dict:
        """JWT ile ilgili ayarları dict olarak döner (AI / generator için uygun)."""
        return {
            "secret_key": self.secret_key,
            "refresh_secret_key": self.refresh_secret_key,
            "algorithm": self.algorithm,
            "access_token_expire_minutes": self.access_token_expire_minutes,
            "refresh_token_expire_days": self.refresh_token_expire_days,
            "jwt_issuer": self.jwt_issuer,
            "jwt_audience": self.jwt_audience,
        }


# Global settings instance
settings = Settings()


if __name__ == "__main__":
    # Küçük bir özet, local debug için işe yarar
    print("🔧 Settings Summary")
    print(f"  App: {settings.app_name} v{settings.app_version}")
    print(f"  Env: {settings.environment} (debug={settings.debug})")
    print(f"  DB:  {settings.async_database_url}")
    print(f"  JWT: access={settings.access_token_expire_minutes}min, refresh={settings.refresh_token_expire_days}days")
    print(f"  CORS Origins: {settings.cors_origins}")
    print(f"  AI Provider: {settings.DEFAULT_AI_PROVIDER}, Gemini Key set? {bool(settings.GEMINI_API_KEY)}, OpenAI Key set? {bool(settings.OPENAI_API_KEY)}")
