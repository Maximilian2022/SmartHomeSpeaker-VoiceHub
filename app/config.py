import os
import socket
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

import sys
import tempfile

BASE_DIR = Path(__file__).resolve().parent.parent

# テスト実行環境の自動検出とデータ分離保護
if "VOICEHUB_DATA_DIR" not in os.environ:
    if "unittest" in sys.modules or "pytest" in sys.modules or any("unittest" in a or "pytest" in a for a in sys.argv):
        _test_tmp = Path(tempfile.gettempdir()) / "voicehub_test_env"
        os.environ["VOICEHUB_DATA_DIR"] = str(_test_tmp / "data")
        os.environ["VOICEHUB_LOG_DIR"] = str(_test_tmp / "logs")

DATA_DIR = Path(os.environ.get("VOICEHUB_DATA_DIR", BASE_DIR / "data"))
LOG_DIR = Path(os.environ.get("VOICEHUB_LOG_DIR", "/logs" if Path("/logs").exists() else BASE_DIR / "logs"))
PUBLIC_DIR = BASE_DIR / "public"
VOICE_DIR = PUBLIC_DIR / "voice"
SOUND_DIR = PUBLIC_DIR / "sound"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DIR.mkdir(parents=True, exist_ok=True)
SOUND_DIR.mkdir(parents=True, exist_ok=True)

def auto_detect_local_ip() -> str:
    """LAN内のプライベートIPアドレスを自動検出"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class Settings(BaseSettings):
    tz: str = Field(default="Asia/Tokyo", alias="TZ")
    server_port: int = Field(default=8080, alias="SERVER_PORT")
    port: int = Field(default=8080, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    
    wireless_ip: str = Field(default="", alias="WIRELESS_IP")
    wireless_module_name: str = Field(default="", alias="WIRELESS_MODULE_NAME")
    
    default_speaker_ip: str = Field(default="", alias="DEFAULT_SPEAKER_IP")
    google_home_ip: str = Field(default="", alias="GOOGLE_HOME_IP")
    default_voice: str = Field(default="ja-JP-NanamiNeural", alias="DEFAULT_VOICE")
    max_cache_size_mb: int = Field(default=1024, alias="MAX_CACHE_SIZE_MB")
    
    webhook_token: str = Field(default="", alias="WEBHOOK_TOKEN")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD")
    web_password: str = Field(default="", alias="WEB_PASSWORD")
    tunnel_domain: str = Field(default="", alias="CLOUDFLARE_TUNNEL_DOMAIN")
    
    alexa_enabled: bool = Field(default=False, alias="ALEXA_ENABLED")
    alexa_default_device: str = Field(default="ALL", alias="ALEXA_DEFAULT_DEVICE")
    refresh_token: str = Field(default="", alias="REFRESH_TOKEN")
    
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    
    go2rtc_api_url: str = Field(default="http://127.0.0.1:1984", alias="GO2RTC_API_URL")
    
    watchtower_url: str = Field(default="http://127.0.0.1:8082", alias="WATCHTOWER_URL")
    watchtower_token: str = Field(default="voicehub-watchtower-token", alias="WATCHTOWER_TOKEN")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".my.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_wireless_ip(self) -> str:
        return self.wireless_ip or auto_detect_local_ip()

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
