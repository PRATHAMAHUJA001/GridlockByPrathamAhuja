from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "TrafficSarathi"
    DATABASE_URL: str = "sqlite:///./traffic_violations.db"
    SECRET_KEY: str = "hackathon-secret-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    EVIDENCE_DIR: Path = BASE_DIR / "evidence"
    ML_MODELS_DIR: Path = BASE_DIR / "ml_models"

    CONFIDENCE_THRESHOLD: float = 0.35

    # Comma-separated list of allowed CORS origins; defaults to localhost dev server.
    # In production set this to your Vercel frontend URL, e.g.:
    #   ALLOWED_ORIGINS=https://trafficsarathi.vercel.app
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.EVIDENCE_DIR.mkdir(exist_ok=True)
