"""
Central place for reading configuration from environment variables.
Nothing in this file should ever contain a real secret — values come
from .env at runtime (see .env.example for the template).
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database (same DB the PHP app uses)
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_user: str = os.getenv("DB_USER", "root")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_name: str = os.getenv("DB_NAME", "if0_40252865_user_db")

    # Model artifacts
    model_dir: str = os.getenv("MODEL_DIR", "./models_store")

    # SBERT
    sbert_model_name: str = os.getenv("SBERT_MODEL_NAME", "all-MiniLM-L6-v2")

    # API server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()

