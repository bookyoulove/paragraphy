"""애플리케이션 설정.

리포지토리 루트의 .env 를 읽어온다 (backend/ 가 아니라 프로젝트 루트에 위치).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    bareun_api_key: str = ""
    bareun_host: str = "api.bareun.ai"
    bareun_port: int = 443

    # 학교 AI Cloud 게이트웨이 (OpenAI 호환 API, POST /v1/chat/completions).
    # openai 파이썬 라이브러리로 호출하되 base_url/api_key만 게이트웨이로 교체한다.
    ai_cloud_api_key: str = ""
    ai_cloud_base_url: str = "https://mlapi.run/e9a5f41b-fdda-44f2-9545-ed88c458da53/v1"
    ai_cloud_model: str = "anthropic/claude-sonnet-5"

    database_url: str = f"sqlite:///{REPO_ROOT / 'backend' / 'paragraphy.db'}"


settings = Settings()