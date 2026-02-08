from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaVideo
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.queries.movie.favorite_movies import FavoriteMoviesActions
from src.app.database.queries.movie.mini_series import MiniSeriesActions
from src.app.database.queries.movie.series import SeriesActions
from src.app.keyboards.callback_data import SeriesPlayerCD, FeatureFilmPlayerCD, MiniSeriesPlayerCD
from src.app.keyboards.inline import series_player_kbd, film_kbd, mini_series_player_kbd

player_router = Router()


@player_router.callback_query(F.data == "close")
async def clouuse_window(call: CallbackQuery):
    await call.message.delete()


@player_router.callback_query(SeriesPlayerCD.filter())
async def series_player(call: CallbackQuery, session: AsyncSession, callback_data: SeriesPlayerCD):
    series_actions = SeriesActions(session)
    favorites_actions = FavoriteMoviesActions(session)

    # get_series allaqachon season va series bo'yicha tartiblangan
    series_data = await series_actions.get_series(callback_data.code)


    current_series = next(
        (s for s in series_data
         if s.season == callback_data.season_number and s.series == callback_data.series_number),
        None
    )

    if current_series is None:
        await call.answer("❌ Qism topilmadi", show_alert=True)
        return

    current_index = next(
        (i for i, s in enumerate(series_data, start=1)
         if s.season == callback_data.season_number and s.series == callback_data.series_number),
        1
    )

    series_count_for_current_season = sum(1 for s in series_data if s.season == callback_data.season_number)

    series_count = len(series_data)
    # seasons_count = max(s[2] for s in series_data) -> s.season
    # Handle empty list case if needed, but assuming series_data exists if we are here
    seasons_count = max(s.season for s in series_data) if series_data else 0

    user_id = call.from_user.id
    saved = await favorites_actions.get_favorites(callback_data.code, user_id)

    if callback_data.action == "save_to_favorites":
        await favorites_actions.add_favorite_movie(callback_data.code, user_id)
        saved = True
    elif callback_data.action == "remove_in_favorites":
        await favorites_actions.delete_favorite_movie(callback_data.code, user_id)
        saved = False

    await call.message.edit_media(
        InputMediaVideo(
            media=current_series.video_file_id,
            caption=current_series.captions
        ),
        reply_markup=series_player_kbd(
            code=callback_data.code,
            current_series=current_index,
            series_count=series_count,
            current_season=callback_data.season_number,
            seasons_count=seasons_count,
            current_series_for_current_season=callback_data.series_number,
            series_count_for_current_season=series_count_for_current_season,
            saved=bool(saved)
        )
    )


@player_router.callback_query(FeatureFilmPlayerCD.filter())
async def feature_movies_player(call: CallbackQuery, callback_data: FeatureFilmPlayerCD, session: AsyncSession):
    favorite_films_actions = FavoriteMoviesActions(session)

    saved = await favorite_films_actions.get_favorites(callback_data.code, call.from_user.id)
    saved = True if saved else False


    if callback_data.actions == "delete_for_favorites" and saved:
        await favorite_films_actions.delete_favorite_movie(callback_data.code, call.from_user.id)
        await call.message.edit_reply_markup(
            reply_markup=film_kbd(callback_data.code, False)
        )
        return await call.answer("❌ Film sevimlilardan o‘chirildi")

    if callback_data.actions == "add_to_favorites" and not saved:
        await favorite_films_actions.add_favorite_movie(callback_data.code, call.from_user.id)
        await call.message.edit_reply_markup(
            reply_markup=film_kbd(callback_data.code, True)
        )
        return await call.answer("💾 Film sevimlilarga qo‘shildi")


@player_router.callback_query(MiniSeriesPlayerCD.filter())
async def mini_series_player(call: CallbackQuery, callback_data: MiniSeriesPlayerCD, session: AsyncSession):
    favorite_films_actions = FavoriteMoviesActions(session)
    mini_series_actions = MiniSeriesActions(session)

    saved = await favorite_films_actions.get_favorites(callback_data.code, call.from_user.id)
    mini_series_data = await mini_series_actions.get_mini_series(callback_data.code)
    current_series = None
    for series in mini_series_data:
        # series is MiniSeries object. series.series (column) matches callback data
        if series.series == callback_data.series_number:
            current_series = series
    saved = bool(saved)

    if not current_series:
         await call.answer("❌ Seria topilmadi", show_alert=True)
         return

    if callback_data.action == "delete_for_favorites" and saved:
        await favorite_films_actions.delete_favorite_movie(callback_data.code, call.from_user.id)
        # current_series[3] -> current_series.video_file_id
        # current_series[-1] -> current_series.captions
        # current_series[2] -> current_series.series
        await call.message.edit_media(
            InputMediaVideo(media=current_series.video_file_id, caption=current_series.captions),
            reply_markup=mini_series_player_kbd(callback_data.code, current_series.series, len(mini_series_data), False)
        )
        return await call.answer("❌ Film sevimlilardan o‘chirildi")

    if callback_data.action == "add_to_favorites" and not saved:
        await favorite_films_actions.add_favorite_movie(callback_data.code, call.from_user.id)
        await call.message.edit_media(
            InputMediaVideo(media=current_series.video_file_id, caption=current_series.captions),
            reply_markup=mini_series_player_kbd(callback_data.code, current_series.series, len(mini_series_data), True)
        )
        return await call.answer("💾 Film sevimlilarga qo‘shildi")

    if callback_data.action == "next_series":
        await call.message.edit_media(
            InputMediaVideo(media=current_series.video_file_id, caption=current_series.captions),
            reply_markup=mini_series_player_kbd(callback_data.code, current_series.series, len(mini_series_data), saved)
        )

    if callback_data.action == "back_series":
        await call.message.edit_media(
            InputMediaVideo(media=current_series.video_file_id, caption=current_series.captions),
            reply_markup=mini_series_player_kbd(callback_data.code, current_series.series, len(mini_series_data), saved)
        )
