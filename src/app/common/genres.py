"""
Genre management module for Movie Bot.

This module contains all genre-related constants, configurations, and helper functions.
"""

import json
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# All available genres with their emojis
GENRES = [
    {"name": "Драма", "name_uz": "Drama", "emoji": "🎭", "display": "🎭 Драма", "display_uz": "🎭 Drama"},
    {"name": "Комедия", "name_uz": "Komediya", "emoji": "😂", "display": "😂 Комедия", "display_uz": "😂 Komediya"},
    {"name": "Боевик", "name_uz": "Jangari", "emoji": "💥", "display": "💥 Боевик", "display_uz": "💥 Jangari"},
    {"name": "Триллер", "name_uz": "Triller", "emoji": "😱", "display": "😱 Триллер", "display_uz": "😱 Triller"},
    {"name": "Ужасы", "name_uz": "Qo'rqinchli", "emoji": "👻", "display": "👻 Ужасы", "display_uz": "👻 Qo'rqinchli"},
    {"name": "Фантастика", "name_uz": "Fantastika", "emoji": "🚀", "display": "🚀 Фантастика", "display_uz": "🚀 Fantastika"},
    {"name": "Фэнтези", "name_uz": "Fentezi", "emoji": "🧙", "display": "🧙 Фэнтези", "display_uz": "🧙 Fentezi"},
    {"name": "Мелодрама", "name_uz": "Melodrama", "emoji": "❤️", "display": "❤️ Мелодрама", "display_uz": "❤️ Melodrama"},
    {"name": "Детектив", "name_uz": "Detektiv", "emoji": "🕵️", "display": "🕵️ Детектив / Криминал", "display_uz": "🕵️ Detektiv"},
    {"name": "Приключения", "name_uz": "Sarguzasht", "emoji": "🗺️", "display": "🗺️ Приключения", "display_uz": "🗺️ Sarguzasht"},
    {"name": "Семейный", "name_uz": "Oilaviy", "emoji": "👨‍👩‍👧", "display": "👨‍👩‍👧 Семейный", "display_uz": "👨‍👩‍👧 Oilaviy"},
    {"name": "Мультфильм", "name_uz": "Multfilm", "emoji": "🐭", "display": "🐭 Мультфильм", "display_uz": "🐭 Multfilm"},
    {"name": "Исторический", "name_uz": "Tarixiy", "emoji": "🏛️", "display": "🏛️ Исторический", "display_uz": "🏛️ Tarixiy"},
    {"name": "Документальный", "name_uz": "Hujjatli", "emoji": "📚", "display": "📚 Документальный", "display_uz": "📚 Hujjatli"},
    {"name": "Военный", "name_uz": "Harbiy", "emoji": "⚔️", "display": "⚔️ Военный", "display_uz": "⚔️ Harbiy"},
]


def serialize_genres(genres: List[str]) -> str:
    """
    Convert list of genre names to JSON string for database storage.
    
    Args:
        genres: List of genre names
        
    Returns:
        JSON string representation
    """
    return json.dumps(genres, ensure_ascii=False)


def deserialize_genres(genres_json: Optional[str]) -> List[str]:
    """
    Convert JSON string from database to list of genre names.
    
    Args:
        genres_json: JSON string from database
        
    Returns:
        List of genre names, empty list if None or invalid
    """
    if not genres_json:
        return []
    try:
        return json.loads(genres_json)
    except (json.JSONDecodeError, TypeError):
        return []


def get_genre_display_text(genres: List[str], lang: str = "uz") -> str:
    """
    Get formatted display text for selected genres.
    
    Args:
        genres: List of genre names (technical names in Russian)
        lang: Language to display in ('uz' or 'ru')
        
    Returns:
        Formatted string with emojis
    """
    if not genres:
        return "Janr tanlanmagan" if lang == "uz" else "Жанр не выбран"
    
    if lang == "uz":
        genre_dict = {g["name"]: (g["emoji"], g["name_uz"]) for g in GENRES}
    else:
        genre_dict = {g["name"]: (g["emoji"], g["name"]) for g in GENRES}

    display_genres = []
    for g in genres:
        emoji, name = genre_dict.get(g, ("", g))
        display_genres.append(f"{emoji} {name}")
    
    return ", ".join(display_genres)
