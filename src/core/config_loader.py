# src/core/config_loader.py
import json
import os
from pathlib import Path


def load_settings(config_dir: Path):
    settings_path = config_dir / "settings.json"
    with open(settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 환경변수 자동 치환
    def resolve(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.getenv(env_name)
        return value

    for k, v in data.items():
        data[k] = resolve(v)

    return data
