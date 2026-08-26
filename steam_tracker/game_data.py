import json
from pathlib import Path

_DATA_FILE = Path(__file__).with_name("game_data.json")


def _load_game_data():
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    corrections = data["game_name_corrections"]
    popular_games = [
        (game["app_id"], game["core_name"], game.get("volume"), game.get("subtitle"))
        for game in data["popular_games"]
    ]
    return corrections, popular_games

GAME_NAME_CORRECTIONS, POPULAR_GAMES = _load_game_data()
