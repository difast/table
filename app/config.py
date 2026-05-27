from pydantic_settings import BaseSettings
import os

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
DB_PATH = os.path.join(DATA_DIR, "trades.db")
BOT_CONFIG_PATH = os.path.join(DATA_DIR, "bot_config.json")

class Settings(BaseSettings):
    data_dir: str = DATA_DIR
    db_path: str = DB_PATH
    bot_config_path: str = BOT_CONFIG_PATH
    # Optional: API key for securing this bot's own endpoints
    dashboard_secret: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
