import logging
import os
from typing import Optional
import yaml

class Config:
    _instance: Optional["Config"] = None
    _data: dict = {}

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = self._default_config()
            self._save_config()

    def _default_config(self) -> dict:
        return {
            "app": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": True
            },
            "scraper": {
                "timeout": 10,
                "max_retries": 3,
                "retry_delay": 2
            },
            "nlp": {
                "max_keywords": 10,
                "language": "it",
                "use_google": False
            },
            "db": {
                "use_firestore": False,
                "local_db_file": "local_db.json"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }

    def _save_config(self) -> None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False)

    def get(self, *keys: str, default=None):
        value = self._data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    def setup_logging(self) -> None:
        level = self.get("logging", "level", default="INFO")
        fmt = self.get("logging", "format", default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=fmt)