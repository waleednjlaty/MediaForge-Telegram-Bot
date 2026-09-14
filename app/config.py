from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    database_path: str = "data/mediaforge.db"
    max_file_mb: int = 49
    download_concurrency: int = 2
    rate_limit_count: int = 8
    rate_limit_window_seconds: int = 60
    force_sub_channel: str = ""
    force_sub_join_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admins(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

    def ensure_dirs(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path("downloads").mkdir(parents=True, exist_ok=True)
