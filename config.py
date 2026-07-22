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

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or "postgresql://postgres:postgres@localhost:5432/downloadvid_db"
    )


class ProductionConfig(Config):
    DEBUG = False

    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    # Render may provide postgres:// instead of postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url


# Automatically choose configuration
if os.environ.get("RENDER"):
    active_config = ProductionConfig
else:
    active_config = DevelopmentConfig


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": active_config
}