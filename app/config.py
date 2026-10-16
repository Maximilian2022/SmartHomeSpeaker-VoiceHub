import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "public"
VOICE_DIR = PUBLIC_DIR / "voice"
SOUND_DIR = PUBLIC_DIR / "sound"

DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    port: int = Field(default=8080, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    
    default_speaker_ip: str = Field(default="", alias="DEFAULT_SPEAKER_IP")
    google_home_ip: str = Field(default="", alias="GOOGLE_HOME_IP")
    
    webhook_token: str = Field(default="", alias="WEBHOOK_TOKEN")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD")
    web_password: str = Field(default="", alias="WEB_PASSWORD")
    tunnel_domain: str = Field(default="", alias="TUNNEL_DOMAIN")
    
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    
    go2rtc_api_url: str = Field(default="http://127.0.0.1:1984", alias="GO2RTC_API_URL")
    refresh_token: str = Field(default="", alias="REFRESH_TOKEN")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".my.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_default_ip(self) -> str:
        return self.default_speaker_ip or self.google_home_ip or ""

    @property
    def effective_admin_password(self) -> str:
        return self.admin_password or self.web_password or ""

    @property
    def effective_gemini_key(self) -> str:
        return self.gemini_api_key or self.ai_api_key or ""

settings = Settings()
