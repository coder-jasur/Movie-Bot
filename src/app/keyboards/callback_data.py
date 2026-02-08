import enum

from aiogram.filters.callback_data import CallbackData


class FeatureFilmPlayerCD(CallbackData, prefix="feature_film_player"):
    code: int
    actions: str

class MiniSeriesPlayerCD(CallbackData, prefix="mini_series_player"):
    code: int
    series_number: int
    action: str

class SeriesPlayerCD(CallbackData, prefix="series_player"):
    code: int
    series_number: int
    season_number: int
    all_series_numebr: int
    action: str


class ActionType(str, enum.Enum):
    back_series = "back_series"
    next_series = "next_series"
    back_season = "back_season"
    next_season = "next_season"
    save_to_favorites = "save_to_favorites"
    remove_in_favorites = "remove_in_favorites"


class ReferralCD(CallbackData, prefix="referral"):
    action: str
    id: int = 0
