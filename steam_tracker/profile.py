import json
import os

from .config import CONFIG_FILE


def load_profile():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_profile(api_key, steam_id, app_id):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"api_key": api_key, "steam_id": steam_id, "app_id": app_id},
                f,
                ensure_ascii=False,
                indent=4,
            )
    except Exception:
        pass
