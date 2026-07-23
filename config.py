import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "plimsoltechstacks")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DOWNLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "downloads"
    )

    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB


class DevelopmentConfig(Config):
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/downloadvid_db"
    )

    # Fix old Render DATABASE_URL format
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )


class ProductionConfig(Config):
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    # Fix old Render DATABASE_URL format
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": ProductionConfig
}