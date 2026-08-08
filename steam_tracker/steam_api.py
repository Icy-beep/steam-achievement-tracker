import requests

from .config import STEAM_API_ACHIEVEMENTS, STEAM_API_SCHEMA


class SteamApiError(Exception):
    pass


def fetch_player_achievements(api_key, steam_id, app_id, timeout=15):
    response = requests.get(
        STEAM_API_ACHIEVEMENTS,
        params={"appid": app_id, "key": api_key, "steamid": steam_id, "l": "russian"},
        timeout=timeout,
    )

    if response.status_code == 400:
        raise SteamApiError("Ошибка 400: Проверьте Steam ID (17 цифр) и App ID.")
    if response.status_code == 403:
        raise SteamApiError("Ошибка 403: Неверный API-ключ или закрытый профиль.")
    if response.status_code != 200 or not response.text.strip():
        raise SteamApiError("Steam вернул пустой ответ.")

    data = response.json()
    playerstats = data.get("playerstats", {})
    if not playerstats.get("success", True):
        raise SteamApiError(f"Steam вернул ошибку: {playerstats.get('error', 'Неизвестная ошибка')}")

    achievements = playerstats.get("achievements", [])
    if not achievements:
        raise SteamApiError("Достижения не найдены. Убедитесь, что вы запускали игру.")

    return achievements


def fetch_achievement_schema(api_key, app_id, timeout=15):
    try:
        response = requests.get(
            STEAM_API_SCHEMA,
            params={"key": api_key, "appid": app_id, "l": "russian"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return {}, "", {}

        data = response.json()
        game_name = data.get("game", {}).get("gameName", "")

        display_names = {}
        descriptions = {}
        for achievement in data.get("game", {}).get("availableGameStats", {}).get("achievements", []):
            tech_name = achievement["name"]
            display_names[tech_name] = achievement.get("displayName", tech_name)
            descriptions[tech_name] = achievement.get("description") or "(Описание отсутствует)"

        return display_names, game_name, descriptions
    except Exception:
        return {}, "", {}
