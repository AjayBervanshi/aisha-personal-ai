import requests
from src.skills.skill_registry import aisha_skill

@aisha_skill
def get_weather(location: str) -> str:
    """Gets the current weather for a given location using wttr.in (No API key required)"""
    try:
        url = f"https://wttr.in/{location.replace(' ', '+')}?format=3"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        return f"Sorry Aju, I couldn't check the weather for {location} right now! ({e})"
