from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.app.keyboards.callback_data import SeriesPlayerCD, FeatureFilmPlayerCD, \
    MiniSeriesPlayerCD, ActionType


def series_player_kbd(
        code: int,
        current_series: int,
        series_count: int,
        current_season: int,
        seasons_count: int,
        current_series_for_current_season: int,
        series_count_for_current_season: int,
        saved: bool,
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    nav_buttons = []

    if int(current_series_for_current_season) > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi Seria",
                callback_data=SeriesPlayerCD(
                    code=code,
                    series_number=current_series_for_current_season - 1,
                    season_number=current_season,
                    all_series_numebr=current_series - 1,
                    action=ActionType.back_series
                ).pack()
            )
        )

    # Серия номер
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_series_for_current_season}/{series_count_for_current_season}",
            callback_data="noop"
        )
    )

    # Следующая серия
    if current_series_for_current_season < series_count_for_current_season:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Keyingi seria ➡️",
                callback_data=SeriesPlayerCD(
                    code=code,
                    series_number=current_series_for_current_season + 1,
                    season_number=current_season,
                    all_series_numebr=current_series + 1,
                    action=ActionType.next_series
                ).pack()
            )
        )

    keyboard.row(*nav_buttons)

    # 🔢 Общий номер серии (например 4/30)
    if series_count > 1:
        keyboard.row(
            InlineKeyboardButton(
                text=f"{current_series}/{series_count}",
                callback_data="noop"
            )
        )

    # 📺 Навигация по сезонам
    season_buttons = []
    if seasons_count > 1:
        # Предыдущий сезон
        if current_season > 1:
            season_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Oldingi Fasl",
                    callback_data=SeriesPlayerCD(
                        code=code,
                        series_number=1,
                        season_number=current_season - 1,
                        all_series_numebr=current_series,
                        action=ActionType.back_season
                    ).pack()
                )
            )

        # Номер сезона
        if seasons_count > 1:
            season_buttons.append(
                InlineKeyboardButton(
                    text=f"{current_season}/{seasons_count}",
                    callback_data="noop"
                )
            )

        # Следующий сезон
        if current_season < seasons_count:
            season_buttons.append(
                InlineKeyboardButton(
                    text="Keyingi Fasl ➡️",
                    callback_data=SeriesPlayerCD(
                        code=code,
                        series_number=1,
                        season_number=current_season + 1,
                        all_series_numebr=current_series,
                        action=ActionType.next_season
                    ).pack()
                )
            )

        keyboard.row(*season_buttons)

    # ⭐ Кнопка избранного
    if saved:
        keyboard.row(
            InlineKeyboardButton(
                text="🗑 O'chirish",
                callback_data=SeriesPlayerCD(
                    code=code,
                    series_number=current_series_for_current_season,
                    season_number=current_season,
                    all_series_numebr=current_series,
                    action=ActionType.remove_in_favorites
                ).pack()
            )
        )
    else:
        keyboard.row(
            InlineKeyboardButton(
                text="💾 Saqlash",
                callback_data=SeriesPlayerCD(
                    code=code,
                    series_number=current_series_for_current_season,
                    season_number=current_season,
                    all_series_numebr=current_series,
                    action=ActionType.save_to_favorites
                ).pack()
            )
        )

    keyboard.row(InlineKeyboardButton(
        text="❌", callback_data="close"
    ))

    return keyboard.as_markup()


def film_kbd(code: int, saved: bool) -> InlineKeyboardMarkup:
    inline_keyboard = InlineKeyboardBuilder()

    film_kbd_clouse_for_series = InlineKeyboardButton(
        text="❌", callback_data="close"
    )

    if saved:
        add_to_favorites = InlineKeyboardButton(
            text="🗑 O'chirish",
            callback_data=FeatureFilmPlayerCD(
                code=code,
                actions="delete_for_favorites"
            ).pack()
        )
    else:
        add_to_favorites = InlineKeyboardButton(
            text="💾 Saqlash",
            callback_data=FeatureFilmPlayerCD(
                code=code,
                actions="add_to_favorites"
            ).pack()
        )

    inline_keyboard.row(add_to_favorites)
    inline_keyboard.row(film_kbd_clouse_for_series)

    return inline_keyboard.as_markup()


def mini_series_player_kbd(code: int, current_seria: int, serias_count: int, saved: bool) -> InlineKeyboardMarkup:
    inline_keyboard = InlineKeyboardBuilder()

    serias_info_button = InlineKeyboardButton(text=f'{current_seria}/{serias_count}', callback_data="serias_info")
    next_button = InlineKeyboardButton(
        text='Keyingi Seria ⏭️',
        callback_data=MiniSeriesPlayerCD(code=code, series_number=current_seria + 1,
                                         action=ActionType.next_series).pack()
    )
    previous_button = InlineKeyboardButton(
        text='⏮️ Orqaga',
        callback_data=MiniSeriesPlayerCD(code=code, series_number=current_seria - 1,
                                         action=ActionType.back_series).pack()
    )

    film_kbd_clouse_for_series = InlineKeyboardButton(
        text="❌", callback_data="close"
    )

    if saved:
        add_to_favorites = InlineKeyboardButton(
            text="🗑 O'chirish",
            callback_data=MiniSeriesPlayerCD(
                code=code,
                series_number=current_seria,
                action="delete_for_favorites"
            ).pack()
        )
    else:
        add_to_favorites = InlineKeyboardButton(
            text="💾 Saqlash",
            callback_data=MiniSeriesPlayerCD(
                code=code,
                series_number=current_seria,
                action="add_to_favorites"
            ).pack()
        )

    if serias_count > 1:
        if current_seria == 1:
            inline_keyboard.row(serias_info_button, next_button)
        elif 1 < current_seria < serias_count:
            inline_keyboard.row(previous_button, serias_info_button, next_button)
        else:
            inline_keyboard.row(previous_button, serias_info_button)

    inline_keyboard.row(add_to_favorites)
    inline_keyboard.row(film_kbd_clouse_for_series)

    return inline_keyboard.as_markup()





start_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Telegram", url="https://t.me/KinoLentaUzb")
        ]
    ]
)


def not_channels_button(channel_data, bots_data):
    builder_button = InlineKeyboardBuilder()
    for bot in bots_data:
        # bot is Bot object
        builder_button.row(
            InlineKeyboardButton(text=bot.bot_name, url=bot.bot_url)
        )
    for channel in channel_data:
        # channel is Channel object
        builder_button.row(
            InlineKeyboardButton(text=channel.channel_name, url=channel.channel_url)
        )

    builder_button.row(InlineKeyboardButton(text="✅", callback_data="check_sub"))
    return builder_button.as_markup()


instagram_channel_kbd = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Instagram Kanal",
                url="https://www.instagram.com/film.zonasi/"
            )
        ]
    ]
)
