import html
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.queries.movie.favorite_movies import FavoriteMoviesActions
from src.app.database.queries.movie.feature_films import FeatureFilmsActions
from src.app.database.queries.movie.mini_series import MiniSeriesActions
from src.app.database.queries.movie.series import SeriesActions

logger = logging.getLogger(__name__)
favorite_movies_router = Router()

@favorite_movies_router.message(Command("favorites"))
async def list_favorite_movies(message: Message, session: AsyncSession):
    try:
        favorites_actions = FavoriteMoviesActions(session)
        favorite_films_data = await favorites_actions.get_all_favorites_by_user_id(user_id=message.from_user.id)

        if not favorite_films_data:
            await message.answer("😔 <b>Siz hali hech nima saqlamagansiz</b>", parse_mode="HTML")
            return

        texts = "📬 <b>Sizning filmlar to'plamingiz</b>\n"
        texts += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        feature_movies_actions = FeatureFilmsActions(session)
        mini_series_actions = MiniSeriesActions(session)
        series_actions = SeriesActions(session)

        for favorite_film_data in favorite_films_data:
            movie_code = favorite_film_data.movie_code

            # Try to find the movie in any table
            feature = await feature_movies_actions.get_feature_film(movie_code)
            if feature:
                texts += f"🎬 <b>{html.escape(feature.name)}</b>\n"
                texts += f"└ 🆔 Kod: <code>{movie_code}</code>\n\n"
                continue

            mini = await mini_series_actions.get_mini_series(movie_code)
            if mini:
                texts += f"🧩 <b>{html.escape(mini[0].name)}</b>\n"
                texts += f"└ 🆔 Kod: <code>{movie_code}</code>\n\n"
                continue

            series = await series_actions.get_series(movie_code)
            if series:
                texts += f"📺 <b>{html.escape(series[0].name)}</b>\n"
                texts += f"└ 🆔 Kod: <code>{movie_code}</code>\n\n"
                continue

        texts += "━━━━━━━━━━━━━━━━━━━━━\n"
        texts += "<i>Filmni ko'rish uchun uning kodini botga yuboring.</i>"

        await message.answer(texts, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in list_favorite_movies: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
