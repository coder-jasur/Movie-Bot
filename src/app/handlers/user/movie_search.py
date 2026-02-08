from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.app.core.config import Settings
from src.app.database.models import FeatureFilm, MiniSeries, Series
from src.app.database.queries.movie.favorite_movies import FavoriteMoviesActions
from src.app.database.queries.movie.feature_films import FeatureFilmsActions
from src.app.database.queries.movie.mini_series import MiniSeriesActions
from src.app.database.queries.movie.series import SeriesActions
from src.app.database.queries.movie.top_movies import TopMoviesActions
from src.app.keyboards.inline import film_kbd, mini_series_player_kbd, series_player_kbd, instagram_channel_kbd
from src.app.common.genres import GENRES, get_genre_display_text, deserialize_genres
from src.app.repositories.repository import SearchRepository
from src.app.services.view_tracker import ViewTracker
from src.app.states.user.dialogs import SearchByGenreSG
from src.app.keyboards.replay import random_movies

logger = logging.getLogger(__name__)

movie_search_router = Router()

@movie_search_router.message(F.text.in_(["🎬 Tasodifiy Film", "📺 Tasodifiy Serial", "🍿 Tasodifiy Epizodli Film"]))
async def random_film_handler(message: Message, session: AsyncSession):
    feature_films_actions = FeatureFilmsActions(session)
    mini_series_actions = MiniSeriesActions(session)
    series_actions = SeriesActions(session)

    random_movie = None

    if message.text == "🎬 Tasodifiy Film":
        random_movie = await feature_films_actions.get_random_feature_film()

    elif message.text == "🍿 Tasodifiy Epizodli Film":
        random_movie = await mini_series_actions.get_random_mini_series_first_episode()

    elif message.text == "📺 Tasodifiy Serial":
        random_movie = await series_actions.get_random_series_first_episode()


    if not random_movie:
        await message.answer("😔 Hozircha bu turdagi kontent mavjud emas.")
        return

    favorite_actions = FavoriteMoviesActions(session)
    # Check if saved. random_movie.code is common for all.
    saved = bool(await favorite_actions.get_favorites(random_movie.code, message.from_user.id))

    if isinstance(random_movie, FeatureFilm):
        await message.answer_video(
            video=random_movie.video_file_id,
            caption=random_movie.captions,
            reply_markup=film_kbd(random_movie.code, saved)
        )
        # TRACK VIEW - Random
        await track_and_increment_view(
            user_id=message.from_user.id,
            movie_code=random_movie.code,
            increment_func=lambda: feature_films_actions.increment_views(random_movie.code)
        )
    elif isinstance(random_movie, MiniSeries):
        ms_all = await mini_series_actions.get_mini_series(random_movie.code)
        await message.answer_video(
            video=random_movie.video_file_id,
            caption=random_movie.captions,
            reply_markup=mini_series_player_kbd(random_movie.code, random_movie.series, len(ms_all), saved)
        )
        # TRACK VIEW - Random
        await track_and_increment_view(
            user_id=message.from_user.id,
            movie_code=random_movie.code,
            increment_func=lambda: mini_series_actions.increment_views(random_movie.code, random_movie.series)
        )
    elif isinstance(random_movie, Series):
        s_all = await series_actions.get_series(random_movie.code)
        
        current_season_series = 0
        for s in s_all:
            if s.season == random_movie.season:
                current_season_series += 1
        
        last_ep = s_all[-1]
        
        await message.answer_video(
            video=random_movie.video_file_id,
            caption=random_movie.captions,
            reply_markup=series_player_kbd(
                random_movie.code,
                1, # series iterator (not used much? or used for nav) - wait, this param name in series_player_kbd?
                len(s_all),
                random_movie.season,
                last_ep.season,
                random_movie.series,
                current_season_series,
                saved
            )
        )
        # TRACK VIEW - Random
        await track_and_increment_view(
            user_id=message.from_user.id,
            movie_code=random_movie.code,
            increment_func=lambda: series_actions.increment_views(random_movie.code, random_movie.season, random_movie.series)
        )

@movie_search_router.message(F.text == "🔝 Top Filmlar")
async def top_films_handler(message: Message, session: AsyncSession):
    await send_top_movies(message, session, interval="total")

async def send_top_movies(message: Message, session: AsyncSession, interval: str = "total"):
    """Top filmlarni ko'rsatish - optimallashtirilgan versiya"""
    try:
        # Optimallashtirilgan query - database darajasida agregatsiya
        top_movies_actions = TopMoviesActions(session)
        top_20 = await top_movies_actions.get_top_movies(interval=interval, limit=20)
    except Exception as e:
        logger.error(f"Error getting top movies: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        return

    interval_names = {
        "day": "KUNLIK",
        "week": "HAFTALIK",
        "month": "OYLIK",
        "total": "BARCHA VAQTDAGI"
    }
    
    text = f"🔥 {interval_names.get(interval)} TOP 20 FILMLAR:\n\n"

    if not top_20:
        text += "<i>Hozircha ma'lumotlar yo'q.</i>"
    
    for index, m in enumerate(top_20, start=1):
        text += (
            f"<b>{index}</b>. <b>{m['name']}</b>\n"
            f"   ├─ <b>Turi</b>: <b>{m['type']}</b>\n"
            f"   ├─ <b>Kod</b>: <code>{m['code']}</code>\n"
            f"   ├─ <b>Saqlangan</b>: <b>{m['favs']}</b>\n"
            f"   └─ <b>Ko'rilgan</b>: <b>{m['views']}</b>\n\n"
        )

    await message.answer(text, parse_mode="HTML")


# --- GENRE SEARCH HELPERS ---

def is_genre_button(message: Message) -> bool:
    text = message.text
    if not text:
        return False
    clean_text = text[2:] if text.startswith("✅ ") else text
    return any(g["display_uz"] == clean_text for g in GENRES)

def get_genre_reply_keyboard(selected_genres: list[str]) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    # Top buttons: Search and Back
    builder.row(
        KeyboardButton(text="🔍 Qidirish"),
        KeyboardButton(text="🔙 Orqaga")
    )
    
    # Genre buttons
    genre_buttons = []
    for g in GENRES:
        name = g["name"]
        checkmark = "✅ " if name in selected_genres else ""
        genre_buttons.append(KeyboardButton(text=f"{checkmark}{g['display_uz']}"))
    
    # Grid of genres (2 per row)
    builder.add(*genre_buttons)
    builder.adjust(2) # 2 columns
    
    return builder.as_markup(resize_keyboard=True)

# --- HANDLERS ---

@movie_search_router.message(F.text == "🎭 Janr bo'yicha Film")
async def movies_by_genre(message: Message, state: FSMContext):
    await state.set_state(SearchByGenreSG.select_genres)
    await state.update_data(selected_genres=[])
    await message.answer(
        "🎭 <b>Janrlarni tanlang:</b>\n\n"
        "Bir nechta tanlashingiz mumkin. Tanlab bo'lgach <b>🔍 Qidirish</b> tugmasini bosing.",
        reply_markup=get_genre_reply_keyboard([]),
        parse_mode="HTML"
    )

@movie_search_router.message(SearchByGenreSG.select_genres, F.text == "🔙 Orqaga")
async def genre_search_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=random_movies)

@movie_search_router.message(SearchByGenreSG.select_genres, F.text == "🔍 Qidirish")
async def genre_search_execute(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    selected = data.get("selected_genres", [])
    
    if not selected:
        await message.answer("⚠️ Kamida bitta janrni tanlang!")
        return
    
    top_actions = TopMoviesActions(session)
    results = await top_actions.get_top_by_genres(selected, limit=10)
    
    genre_header = get_genre_display_text(selected, lang="uz")

    text = "🎭 Janrlar bo'yicha qidiruv\n\n"

    text += f"🔎 <b>Janrlar:</b> {genre_header}\n\n"

    if results:
        text += "<b>Top 10 ta mos filmlar:</b>\n\n"
    else:
        text += "😔 <i>Ushbu janr bo‘yicha filmlar topilmadi.</i>\n\n"

    for index, m in enumerate(results, start=1):
        text += (
            f"<b>{index}. {m['name']}</b>\n"
            f"   ├─ <b>Turi:</b> {m['type']}\n"
            f"   ├─ <b>Kod:</b> <code>{m['code']}</code>\n"
            f"   ├─ <b>Saqlangan:</b> {m['favs']}\n"
            f"   └─ <b>Ko‘rilgan:</b> {m['views']}\n\n"
        )

    if results:
        text += "<b>Ko‘rish uchun film kodini yuboring.</b>"

    await message.answer(text, parse_mode="HTML")


@movie_search_router.message(SearchByGenreSG.select_genres, is_genre_button)
async def genre_search_toggle(message: Message, state: FSMContext):
    text = message.text
    # Remove checkmark if exists to get pure genre name
    clean_text = text[2:] if text.startswith("✅ ") else text
    
    # Find matching genre in GENRES list based on display_uz name
    target_genre = None
    for g in GENRES:
        if g["display_uz"] == clean_text:
            target_genre = g["name"]
            break
    
    data = await state.get_data()
    selected = list(data.get("selected_genres", []))
    
    if target_genre in selected:
        selected.remove(target_genre)
    else:
        selected.append(target_genre)
    
    await state.update_data(selected_genres=selected)
    
    selected_display = get_genre_display_text(selected, lang="uz")
    await message.answer(
        f"🎭 <b>Tanlangan janrlar:</b> {selected_display}",
        reply_markup=get_genre_reply_keyboard(selected),
        parse_mode="HTML"
    )


@movie_search_router.message(F.text & ~F.text.startswith("/"))
async def movie_search_handler(message: Message, session: AsyncSession):
    favorite_actions = FavoriteMoviesActions(session)
    feature_films_actions = FeatureFilmsActions(session)
    mini_series_actions = MiniSeriesActions(session)
    series_actions = SeriesActions(session)

    query = message.text.strip()

    # --- SEARCH BY CODE ---
    if query.isdigit():
        code = int(query)
        
        feature_films = await feature_films_actions.get_feature_film(code)
        mini_series = await mini_series_actions.get_mini_series(code)
        series = await series_actions.get_series(code)

        saved = await favorite_actions.get_favorites(code, message.from_user.id)
        saved = bool(saved)

        if feature_films:
            await message.answer_video(
                video=feature_films.video_file_id,
                caption=feature_films.captions,
                reply_markup=film_kbd(code, saved)
            )
            
            await track_and_increment_view(
                user_id=message.from_user.id,
                movie_code=code,
                increment_func=lambda: feature_films_actions.increment_views(code)
            )
            return
        elif mini_series:
            # mini_series is list[MiniSeries]
            await message.answer_video(
                video=mini_series[0].video_file_id,
                caption=mini_series[0].captions,
                reply_markup=mini_series_player_kbd(code, 1, len(mini_series), saved)
            )

            # TRACK VIEW - optimized
            await track_and_increment_view(
                user_id=message.from_user.id,
                movie_code=code,
                increment_func=lambda: mini_series_actions.increment_views(code, 1)
            )
            return
        elif series:
            current_season_series = 0
            for s in series:
                if s.season == 1:
                    current_season_series += 1

            first_ep = series[0]
            last_ep = series[-1]
            
            await message.answer_video(
                video=first_ep.video_file_id,
                caption=first_ep.captions,
                reply_markup=series_player_kbd(
                    code,
                    1, # current global series num
                    len(series), # total series count
                    first_ep.season, # current season
                    last_ep.season, # total seasons count
                    first_ep.series, # current series num in season
                    current_season_series,
                    saved
                )
            )

            # TRACK VIEW - optimized
            await track_and_increment_view(
                user_id=message.from_user.id,
                movie_code=code,
                increment_func=lambda: series_actions.increment_views(code, first_ep.season, first_ep.series)
            )
            return
        else:
            # Not found as code, will search by name
            pass

    # --- SEARCH BY NAME ---
    search_engine = SearchRepository(session)
    results = []

    for film, score in await search_engine.search_feature_films(message.text.lower()):
        genres_text = get_genre_display_text(deserialize_genres(film.genres), lang="uz")
        results.append(f"🎬 <b>{film.name}</b>\n"
                       f"└ 🎭 Janr: <b>{genres_text}</b>\n"
                       f"└ 🆔 Kod: <code>{film.code}</code>\n")

    for series, score in await search_engine.search_series(message.text.lower()):
        genres_text = get_genre_display_text(deserialize_genres(series.genres), lang="uz")
        results.append(f"📺 <b>{series.name}</b>\n"
                       f"└ 🎭 Janr: <b>{genres_text}</b>\n"
                       f"└ 🆔 Kod: <code>{series.code}</code>\n")

    for mini, score in await search_engine.search_mini_series(message.text.lower()):
        genres_text = get_genre_display_text(deserialize_genres(mini.genres), lang="uz")
        results.append(f"🧩 <b>{mini.name}</b>\n"
                       f"└ 🎭 Janr: <b>{genres_text}</b>\n"
                       f"└ 🆔 Kod: <code>{mini.code}</code>\n")

    if not results:
        if query.isdigit():
             await message.answer(
                "😔 Hechnima topilmadi.\n\n"
                "Kiritilgan kod bo'yicha film topilmadi va shu nomdagi film ham yo'q.",
                reply_markup=instagram_channel_kbd
            )
        else:
            await message.answer(
                "😔 Kechirasiz, bu nomdagi film topilmadi.\n\n"
                "Nomini to'g'ri yozganingizni tekshiring yoki kod orqali qidiring.",
                reply_markup=instagram_channel_kbd
            )
    else:
        max_result = 20
        shown_results = results[:max_result]
        
        response_text = "🔎 <b>Qidiruv natijalari:</b>\n\n" + "\n".join(shown_results)
        
        if len(results) > max_result:
            response_text += f"\n\n<i>... va yana {len(results) - max_result} ta natija. Aniqroq qidiring.</i>"
            
        response_text += "\n\n<b>Ko'rish uchun kerakli filmni kodini yuboring.</b>"
        
        await message.answer(response_text)


async def track_and_increment_view(
    user_id: int,
    movie_code: int,
    increment_func,
):

    try:
        settings = Settings()
        if await ViewTracker.is_new_view(settings.redis_url, user_id, movie_code):
            await increment_func()
    except Exception as e:
        logger.error(f"Error tracking view: {e}")

