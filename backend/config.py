import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    claude_api_url: str = os.getenv("CLAUDE_FABLE5_API_URL", "").strip()
    claude_api_key: str = os.getenv("CLAUDE_FABLE5_API_KEY", "").strip()
    bareun_api_key: str = os.getenv("BAREUN_API_KEY", "").strip()
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'paragraphy.db'}")
    environment: str = os.getenv("ENVIRONMENT", "development").strip()

settings = Settings()
