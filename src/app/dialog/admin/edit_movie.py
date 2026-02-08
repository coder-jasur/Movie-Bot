from typing import Any
import html

from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, SwitchTo, Back, Start, Cancel, Column, Select, ScrollingGroup, Group
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.queries.movie.feature_films import FeatureFilmsActions
from src.app.database.queries.movie.series import SeriesActions
from src.app.database.queries.movie.mini_series import MiniSeriesActions
from src.app.states.admin.dialogs import EditMovieSG, AdminMenuSG
from src.app.common.genres import GENRES, serialize_genres, deserialize_genres, get_genre_display_text


# --- Handlers ---

async def on_edit_genres_click(c: CallbackQuery, widget: Any, manager: DialogManager):
    """Called when user clicks 'Edit Genres'. Load current genres first."""
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    
    genres_json = None
    if m_type == "feature_film":
        ff = await FeatureFilmsActions(session).get_feature_film(code)
        genres_json = ff.genres if ff else None
    elif m_type == "series":
        genres_json = await SeriesActions(session).get_genres_by_code(code)
    elif m_type == "mini_series":
        genres_json = await MiniSeriesActions(session).get_genres_by_code(code)
        
    manager.dialog_data["genres"] = deserialize_genres(genres_json)
    
    # Store where we came from to return correctly
    manager.dialog_data["return_state"] = manager.current_context().state
    
    await manager.switch_to(EditMovieSG.edit_genres)


async def on_genre_toggle(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str = None):
    """Handle genre toggle in edit mode."""
    if widget.widget_id == "save_genres":
        session: AsyncSession = manager.middleware_data["session"]
        code = manager.dialog_data["code"]
        m_type = manager.dialog_data["type"]
        genres_list = manager.dialog_data.get("genres", [])
        genres_ser = serialize_genres(genres_list)
        
        if m_type == "feature_film":
            await FeatureFilmsActions(session).update_genres(code, genres_ser)
        elif m_type == "series":
            await SeriesActions(session).update_genres(code, genres_ser)
        elif m_type == "mini_series":
            await MiniSeriesActions(session).update_genres(code, genres_ser)
            
        # Update local cache so summary reflects changes immediately
        if "obj" in manager.dialog_data:
            manager.dialog_data["obj"]["genres"] = genres_ser
            
        await c.answer("✅ Жанры обновлены!")
        await on_back_click(c, widget, manager)
        return

    genre_name = item_id
    if not genre_name: return
    
    # Use a list copy to ensure aiogram-dialog detects the change
    selected = list(manager.dialog_data.get("genres", []))
    if genre_name in selected: 
        selected.remove(genre_name)
    else: 
        selected.append(genre_name)
    manager.dialog_data["genres"] = selected
    await c.answer()


async def on_code_search(m: Message, widget: Any, manager: DialogManager):
    if not m.text.isdigit():
        await m.answer("❌ Введите число!")
        return
    code = int(m.text)
    manager.dialog_data.clear()
    session: AsyncSession = manager.middleware_data["session"]

    # Search in all tables
    ff_actions = FeatureFilmsActions(session)
    s_actions = SeriesActions(session)
    ms_actions = MiniSeriesActions(session)

    # Check Feature Film
    ff = await ff_actions.get_feature_film(code)
    if ff:
        manager.dialog_data["type"] = "feature_film"
        manager.dialog_data["code"] = code
        manager.dialog_data["obj"] = {
            "name": ff.name, 
            "caption": ff.captions, 
            "file_id": ff.video_file_id,
            "genres": ff.genres
        }
        await manager.switch_to(EditMovieSG.select_action)
        return

    # Check Mini Series
    ms = await ms_actions.get_mini_series(code)
    if ms:
        manager.dialog_data["type"] = "mini_series"
        manager.dialog_data["code"] = code
        first_ep = ms[0]
        # Store global data
        manager.dialog_data["obj"] = {
            "name": first_ep.name,
            "genres": first_ep.genres
        }
        await manager.switch_to(EditMovieSG.select_action)
        return

    s = await s_actions.get_series(code)
    if s:
        manager.dialog_data["type"] = "series"
        manager.dialog_data["code"] = code
        first_ep = s[0]
        manager.dialog_data["obj"] = {
            "name": first_ep.name,
            "genres": first_ep.genres
        }
        await manager.switch_to(EditMovieSG.select_action)
        return

    await m.answer("❌ Фильм с таким кодом не найден.")


async def on_back_click(c: CallbackQuery, widget: Button, manager: DialogManager):
    return_state = manager.dialog_data.get("return_state", EditMovieSG.select_action)
    await manager.switch_to(return_state)


async def on_set_return_action(c: CallbackQuery, widget: Any, manager: DialogManager):
    manager.dialog_data["return_state"] = EditMovieSG.select_action


async def on_set_return_details(c: CallbackQuery, widget: Any, manager: DialogManager):
    manager.dialog_data["return_state"] = EditMovieSG.edit_episode_details


async def on_edit_name(m: Message, widget: Any, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    new_name = m.text
    ep_id = manager.dialog_data.get("selected_episode_id")

    try:
        if ep_id:
            # Episode-specific name update
            if m_type == "series":
                s, n = map(int, ep_id.split(":"))
                await SeriesActions(session).update_episode_metadata(code, s, n, name=new_name)
            elif m_type == "mini_series":
                n = int(ep_id)
                await MiniSeriesActions(session).update_episode_metadata(code, n, name=new_name)
            await m.answer("✅ Название серии обновлено!")
            await manager.switch_to(EditMovieSG.edit_episode_details)
        else:
            # Feature Film update
            if m_type == "feature_film":
                await FeatureFilmsActions(session).update_feature_film(code, name=new_name)
                manager.dialog_data["obj"]["name"] = new_name
                await m.answer("✅ Название обновлено!")
                await manager.switch_to(EditMovieSG.select_action)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_edit_caption(m: Message, widget: Any, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    new_caption = m.html_text if m.caption else m.text
    ep_id = manager.dialog_data.get("selected_episode_id")

    try:
        if ep_id:
            # Episode-specific caption update
            if m_type == "series":
                s, n = map(int, ep_id.split(":"))
                await SeriesActions(session).update_episode_metadata(code, s, n, captions=new_caption)
            elif m_type == "mini_series":
                n = int(ep_id)
                await MiniSeriesActions(session).update_episode_metadata(code, n, captions=new_caption)
            await m.answer("✅ Описание серии обновлено!")
            await manager.switch_to(EditMovieSG.edit_episode_details)
        else:
            # Feature Film update
            if m_type == "feature_film":
                await FeatureFilmsActions(session).update_feature_film(code, captions=new_caption)
                manager.dialog_data["obj"]["caption"] = new_caption
                await m.answer("✅ Описание обновлено!")
                await manager.switch_to(EditMovieSG.select_action)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_edit_code(m: Message, widget: Any, manager: DialogManager):
    if not m.text.isdigit():
        await m.answer("❌ Введите число!")
        return

    new_code = int(m.text)
    old_code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    session: AsyncSession = manager.middleware_data["session"]
    ep_id = manager.dialog_data.get("selected_episode_id")

    try:
        if ep_id:
            # Episode-specific code update -> Move to FeatureFilm
            if m_type == "series":
                s, n = map(int, ep_id.split(":"))
                await SeriesActions(session).move_to_feature_film(old_code, s, n, new_code)
            elif m_type == "mini_series":
                n = int(ep_id)
                await MiniSeriesActions(session).move_to_feature_film(old_code, n, new_code)

            await m.answer(f"✅ Серия отделена и теперь является фильмом с кодом {new_code}!")
            # After separation, we go back to main search or somewhere logical
            await manager.switch_to(EditMovieSG.input_code)
        else:
            # Global code rename (only for feature films or if we ever want global series rename)
            if m_type == "feature_film":
                await FeatureFilmsActions(session).update_movie_code(old_code, new_code)
            elif m_type == "series":
                await SeriesActions(session).update_movie_code(old_code, new_code)
            elif m_type == "mini_series":
                await MiniSeriesActions(session).update_movie_code(old_code, new_code)

            await m.answer(f"✅ Код успешно изменен!")
            manager.dialog_data["code"] = new_code
            await manager.switch_to(EditMovieSG.select_action)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_edit_file(m: Message, widget: Any, manager: DialogManager):
    if m.video:
        file_id = m.video.file_id
    elif m.document:
        file_id = m.document.file_id
    else:
        await m.answer("❌ Пожалуйста, отправьте видео или файл.")
        return

    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    ep_id = manager.dialog_data.get("selected_episode_id")

    try:
        if ep_id:
            if m_type == "series":
                season, num = map(int, ep_id.split(":"))
                await SeriesActions(session).update_episode_file(code, season, num, file_id)
            elif m_type == "mini_series":
                num = int(ep_id)
                await MiniSeriesActions(session).update_episode_file(code, num, file_id)
            await m.answer("✅ Файл серии обновлен!")
            await manager.switch_to(EditMovieSG.edit_episode_details)
        else:
            if m_type == "feature_film":
                await FeatureFilmsActions(session).update_feature_film(code, video_file_id=file_id)
                manager.dialog_data["obj"]["file_id"] = file_id
            await m.answer("✅ Видео обновлено!")
            await manager.switch_to(EditMovieSG.select_action)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_season_selected(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["selected_season"] = int(item_id)
    await manager.switch_to(EditMovieSG.select_episode)


async def on_episode_selected(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["selected_episode_id"] = item_id
    await manager.switch_to(EditMovieSG.edit_episode_details)


async def on_edit_episode_num(m: Message, widget: Any, manager: DialogManager):
    if not m.text.isdigit():
        await m.answer("❌ Введите число!")
        return

    new_num = int(m.text)
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    ep_id = manager.dialog_data["selected_episode_id"]

    try:
        if m_type == "series":
            season, old_num = map(int, ep_id.split(":"))
            eps = await SeriesActions(session).get_series(code)
            if any(e.season == season and e.series == new_num for e in eps):
                await m.answer(f"❌ Серия {new_num} уже занята!")
                return
            await SeriesActions(session).update_episode_details(code, season, old_num, series=new_num)
            manager.dialog_data["selected_episode_id"] = f"{season}:{new_num}"
        elif m_type == "mini_series":
            old_num = int(ep_id)
            eps = await MiniSeriesActions(session).get_mini_series(code)
            if any(e.series == new_num for e in eps):
                await m.answer(f"❌ Серия {new_num} уже занята!")
                return
            await MiniSeriesActions(session).update_episode_details(code, old_num, series=new_num)
            manager.dialog_data["selected_episode_id"] = str(new_num)

        await m.answer("✅ Номер серии обновлен!")
        await manager.switch_to(EditMovieSG.edit_episode_details)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_edit_season_num(m: Message, widget: Any, manager: DialogManager):
    if not m.text.isdigit():
        await m.answer("❌ Введите число!")
        return

    new_season = int(m.text)
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]

    try:
        current_state = manager.current_context().state
        if current_state == EditMovieSG.edit_season_num:  # Individual episode's season
            ep_id = manager.dialog_data["selected_episode_id"]
            season, num = map(int, ep_id.split(":"))
            eps = await SeriesActions(session).get_series(code)
            if any(e.season == new_season and e.series == num for e in eps):
                await m.answer(f"❌ В сезоне {new_season} серия {num} уже есть!")
                return
            await SeriesActions(session).update_episode_details(code, season, num, season=new_season)
            manager.dialog_data["selected_episode_id"] = f"{new_season}:{num}"
            await m.answer("✅ Номер сезона для этой серии обновлен!")
            await manager.switch_to(EditMovieSG.edit_episode_details)
        else:  # Global season rename
            old_season = manager.dialog_data["selected_season"]
            eps = await SeriesActions(session).get_series(code)
            if any(e.season == new_season for e in eps):
                await m.answer(f"❌ Сезон {new_season} уже существует!")
                return
            await SeriesActions(session).update_global_season_selective(code, old_season, new_season)
            manager.dialog_data["selected_season"] = new_season
            await m.answer(f"✅ Сезон {old_season} переименован в {new_season}!")
            await manager.switch_to(EditMovieSG.select_episode)
    except Exception as e:
        await m.answer(f"❌ Ошибка: {e}")


async def on_delete_confirm(c: CallbackQuery, widget: Any, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    try:
        if m_type == "feature_film":
            await FeatureFilmsActions(session).delete_feature_film(code)
        elif m_type == "mini_series":
            await MiniSeriesActions(session).delete_mini_series(code)
        elif m_type == "series":
            await SeriesActions(session).delete_series(code)
        await c.message.answer("✅ Успешно удалено.")
        await manager.switch_to(EditMovieSG.input_code)
    except Exception as e:
        await c.message.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_delete_episode_confirm(c: CallbackQuery, widget: Any, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    m_type = manager.dialog_data["type"]
    selected_ep_id = manager.dialog_data.get("selected_episode_id")
    try:
        if m_type == "series":
            s, n = map(int, selected_ep_id.split(":"))
            await SeriesActions(session).delete_series_for_season(code, n, s)
        elif m_type == "mini_series":
            n = int(selected_ep_id)
            await MiniSeriesActions(session).delete_mini_series_for_series(code, n)
        await c.message.answer("✅ Серия успешно удалена.")
        await manager.switch_to(EditMovieSG.select_episode)
    except Exception as e:
        await c.message.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_delete_season_confirm(c: CallbackQuery, widget: Any, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data["code"]
    season = manager.dialog_data["selected_season"]
    try:
        await SeriesActions(session).delete_season(code, season)
        await c.message.answer(f"✅ Сезон {season} успешно удален.")
        await manager.switch_to(EditMovieSG.select_season)
    except Exception as e:
        await c.message.answer(f"❌ Ошибка: {e}")


# --- Getters ---

async def get_movie_info(dialog_manager: DialogManager, **kwargs):
    session: AsyncSession = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data.get("obj", {})
    code = dialog_manager.dialog_data.get("code")
    m_type = dialog_manager.dialog_data.get("type")

    type_labels = {"feature_film": "🎬 Фильм", "series": "🎞 Сериал", "mini_series": "🎥 Мини-сериал"}
    seasons = []
    episodes = []
    selected_ep = {}
    file_id = data.get("file_id")
    total_eps = 0
    total_seasons = 0

    if m_type == "series":
        eps = await SeriesActions(session).get_series(code)
        total_eps = len(eps)
        unique_seasons = sorted(list(set(e.season for e in eps)))
        total_seasons = len(unique_seasons)
        seasons = [(str(s), f"Сезон {s}") for s in unique_seasons]
        sel_s = dialog_manager.dialog_data.get("selected_season")
        if sel_s:
            s_eps = [e for e in eps if e.season == sel_s]
            episodes = [(f"{e.season}:{e.series}", str(e.series)) for e in s_eps]
        selected_ep_id = dialog_manager.dialog_data.get("selected_episode_id")
        if selected_ep_id:
            try:
                s, n = map(int, selected_ep_id.split(":"))
                match = next((e for e in eps if e.season == s and e.series == n), None)
                if match:
                    selected_ep = {"season": match.season, "episode": match.series, "file_id": match.video_file_id,
                                   "name": match.name, "caption": match.captions, "code": match.code}
                    file_id = match.video_file_id
            except:
                pass
    elif m_type == "mini_series":
        eps = await MiniSeriesActions(session).get_mini_series(code)
        total_eps = len(eps)
        episodes = [(str(e.series), str(e.series)) for e in eps]
        selected_ep_id = dialog_manager.dialog_data.get("selected_episode_id")
        if selected_ep_id:
            try:
                n = int(selected_ep_id)
                match = next((e for e in eps if e.series == n), None)
                if match:
                    selected_ep = {"episode": match.series, "file_id": match.video_file_id, "name": match.name,
                                   "caption": match.captions, "code": match.code}
                    file_id = match.video_file_id
            except:
                pass

    media = None
    if file_id: media = MediaAttachment(type=ContentType.VIDEO, file_id=MediaId(file_id))

    return {
        "code": code, "name": data.get("name"), "caption": data.get("caption"), "type": m_type,
        "type_label": type_labels.get(m_type, "Неизвестно"),
        "is_series": m_type == "series", "is_mini_series": m_type == "mini_series", "is_film": m_type == "feature_film",
        "total_eps": total_eps, "total_seasons": total_seasons, "seasons": seasons, "episodes": episodes,
        "selected_ep": selected_ep, "selected_season": dialog_manager.dialog_data.get("selected_season"), "media": media,
        "genres_text": get_genre_display_text(deserialize_genres(data.get("genres")), lang="ru")
    }


async def get_genre_data(dialog_manager: DialogManager, **kwargs):
    """Getter for genre editing window."""
    selected_genres = dialog_manager.dialog_data.get("genres", [])
    
    genre_list = []
    for g in GENRES:
        name = g["name"]
        checkmark = "✓ " if name in selected_genres else ""
        genre_list.append((name, f"{checkmark}{g['display']}"))
    
    return {
        "name": dialog_manager.dialog_manager.dialog_data.get("obj", {}).get("name"),
        "genres": genre_list,
        "selected_text": get_genre_display_text(selected_genres, lang="ru")
    }


async def get_basic_data(dialog_manager: DialogManager, **kwargs):
    """Основной геттер для окон редактирования"""
    data = dialog_manager.dialog_data.get("obj", {})
    file_id = data.get("file_id")
    media = None
    if file_id:
        media = MediaAttachment(type=ContentType.VIDEO, file_id=MediaId(file_id))
    return {"media": media}


async def get_season_data(dialog_manager: DialogManager, **kwargs):
    """Геттер для ввода сезона"""
    return {
        "media": None,
        "selected_season": dialog_manager.dialog_data.get("selected_season")
    }


# --- Dialog ---

edit_movie_dialog = Dialog(
    Window(
        Format("🔢 <b>Введите код контента (ID):</b>"),
        MessageInput(on_code_search, content_types=ContentType.TEXT),
        Cancel(Const("⬅️ Отмена"), id="cancel"),
        state=EditMovieSG.input_code,
    ),
    Window(
        DynamicMedia("media", when="is_film"),
        Multi(
            Format("📋 <b>ИНФОРМАЦИЯ:</b>\n"
                   "━━━━━━━━━━━━━━━━━━━━━\n"
                    "<b>🏷 Тип:</b> {type_label}\n"
                    "<b>🔢 Код ID:</b> <code>{code}</code>\n"
                    "<b>🎬 Название:</b> <i>{name}</i>\n"
                    "<b>🎭 Жанры:</b> {genres_text}\n"),
            Format("<b>📅 Сезонов:</b> {total_seasons}\n<b>🎞 Серий:</b> {total_eps}\n", when="is_series"),
            Format("<b>🎞 Серий:</b> {total_eps}\n", when="is_mini_series"),
            Format("<b>📄 Описание:</b>\n{caption}\n", when="is_film"),
            Format("━━━━━━━━━━━━━━━━━━━━━\n<b>ДЕЙСТВИЯ:</b>"),
        ),
        Column(
            SwitchTo(Const("✏️ Изменить название"), id="en", state=EditMovieSG.edit_name, when="is_film",
                     on_click=on_set_return_action),
            SwitchTo(Const("📄 Изменить описание"), id="ec", state=EditMovieSG.edit_caption, when="is_film",
                     on_click=on_set_return_action),
            SwitchTo(Const("🔢 Изменить код ID"), id="ecd", state=EditMovieSG.edit_code, on_click=on_set_return_action),
            SwitchTo(Const("📹 Изменить видео"), id="ef", state=EditMovieSG.edit_file, when="is_film",
                     on_click=on_set_return_action),
            Button(Const("🎭 Изменить жанры"), id="eg_btn", on_click=on_edit_genres_click),
            SwitchTo(Const("📅 Управление сезонами"), id="es", state=EditMovieSG.select_season, when="is_series"),
            SwitchTo(Const("🎞 Управление сериями"), id="ee", state=EditMovieSG.select_episode, when="is_mini_series"),
            SwitchTo(Const("🗑 Удалить ПОЛНОСТЬЮ"), id="db", state=EditMovieSG.confirm_delete),
        ),
        SwitchTo(Const("⬅️ К поиску"), id="bm", state=EditMovieSG.input_code),
        state=EditMovieSG.select_action,
        getter=get_movie_info,
    ),
    Window(
        Const("📝 <b>Введите новое название:</b>"),
        MessageInput(on_edit_name, content_types=ContentType.TEXT),
        Button(Const("⬅️ Назад"), id="b1", on_click=on_back_click),
        state=EditMovieSG.edit_name,
        getter=get_basic_data,
    ),
    Window(
        Const("📄 <b>Введите новое описание:</b>"),
        MessageInput(on_edit_caption, content_types=ContentType.TEXT),
        Button(Const("⬅️ Назад"), id="b2", on_click=on_back_click),
        state=EditMovieSG.edit_caption,
        getter=get_basic_data,
    ),
    Window(
        Const("🔢 <b>Введите новый код (ID):</b>"),
        MessageInput(on_edit_code, content_types=ContentType.TEXT),
        Button(Const("⬅️ Назад"), id="b3", on_click=on_back_click),
        state=EditMovieSG.edit_code,
        getter=get_basic_data,
    ),
    Window(
        Const("📹 <b>Отправьте новый видео файл:</b>"),
        MessageInput(on_edit_file, content_types=[ContentType.VIDEO, ContentType.DOCUMENT]),
        Button(Const("⬅️ Назад"), id="b4", on_click=on_back_click),
        state=EditMovieSG.edit_file,
        getter=get_basic_data,
    ),
    Window(
        Const("📅 <b>Выберите сезон:</b>"),
        Group(Select(Format("{item[1]}"), id="s_s", item_id_getter=lambda x: x[0], items="seasons",
                     on_click=on_season_selected), id="sg", width=2),
        SwitchTo(Const("⬅️ Назад"), id="b5", state=EditMovieSG.select_action),
        state=EditMovieSG.select_season,
        getter=get_movie_info,
    ),
    Window(
        Format("🎞 <b>Серии ({selected_season}-й сезон):</b>", when="is_series"),
        Const("🎞 <b>Выберите серию:</b>", when=lambda d, *a: not d["is_series"]),
        Group(Select(Format("{item[1]}"), id="se", item_id_getter=lambda x: x[0], items="episodes",
                     on_click=on_episode_selected), id="eg", width=4),
        Column(
            SwitchTo(Const("🔢 Изменить № сезона"), id="rs", state=EditMovieSG.edit_global_season, when="is_series"),
            SwitchTo(Const("🗑 Удалить ВЕСЬ сезон"), id="ds", state=EditMovieSG.confirm_delete_season, when="is_series"),
        ),
        SwitchTo(Const("⬅️ Назад к сезонам"), id="bs", state=EditMovieSG.select_season, when="is_series"),
        SwitchTo(Const("⬅️ Назад"), id="bm2", state=EditMovieSG.select_action, when=lambda d, *a: not d["is_series"]),
        state=EditMovieSG.select_episode,
        getter=get_movie_info,
    ),
    Window(
        DynamicMedia("media"),
        Multi(
            Format(
                "🛠 <b>СЕРИЯ (Сезон {selected_ep[season]}, Серия {selected_ep[episode]}):</b>\n━━━━━━━━━━━━━━━━━━━━━\n<b>🔢 Код ID:</b> <code>{selected_ep[code]}</code>\n<b>🎬 Название:</b> {selected_ep[name]}\n<b>🎭 Жанры:</b> {genres_text}\n<b>📄 Описание:</b>\n{selected_ep[caption]}",
                when="is_series"),
            Format(
                "🛠 <b>СЕРИЯ (Номер {selected_ep[episode]}):</b>\n━━━━━━━━━━━━━━━━━━━━━\n<b>🔢 Код ID:</b> <code>{selected_ep[code]}</code>\n<b>🎬 Название:</b> {selected_ep[name]}\n<b>🎭 Жанры:</b> {genres_text}\n<b>📄 Описание:</b>\n{selected_ep[caption]}",
                when="is_mini_series"),
        ),
        Column(
            Button(Const("🎭 Изменить жанры"), id="eg_btn_ep", on_click=on_edit_genres_click),
            SwitchTo(Const("📹 Изменить видео файл"), id="ef1", state=EditMovieSG.edit_file,
                     on_click=on_set_return_details),
            SwitchTo(Const("✏️ Изменить название"), id="en1", state=EditMovieSG.edit_name,
                     on_click=on_set_return_details),
            SwitchTo(Const("📄 Изменить описание"), id="ec1", state=EditMovieSG.edit_caption,
                     on_click=on_set_return_details),
            SwitchTo(Const("🔢 Отделить в Фильм (Новый код)"), id="ec2", state=EditMovieSG.edit_code,
                     on_click=on_set_return_details),
            SwitchTo(Const("📅 Изменить номер сезона"), id="es1", state=EditMovieSG.edit_season_num, when="is_series",
                     on_click=on_set_return_details),
            SwitchTo(Const("🔢 Изменить номер серии"), id="en2", state=EditMovieSG.edit_episode_num,
                     on_click=on_set_return_details),
            SwitchTo(Const("🗑 Удалить серию"), id="ed", state=EditMovieSG.confirm_delete_episode),
        ),
        SwitchTo(Const("⬅️ Назад"), id="be", state=EditMovieSG.select_episode),
        state=EditMovieSG.edit_episode_details,
        getter=get_movie_info,
    ),
    Window(
        Const("🔢 <b>Введите новый номер сезона:</b>"),
        MessageInput(on_edit_season_num, content_types=ContentType.TEXT),
        SwitchTo(Const("⬅️ Назад"), id="b6", state=EditMovieSG.edit_episode_details),
        state=EditMovieSG.edit_season_num,
        getter=get_basic_data,
    ),
    Window(
        Const("🔢 <b>Введите новый номер серии:</b>"),
        MessageInput(on_edit_episode_num, content_types=ContentType.TEXT),
        SwitchTo(Const("⬅️ Назад"), id="b7", state=EditMovieSG.edit_episode_details),
        state=EditMovieSG.edit_episode_num,
        getter=get_basic_data,
    ),
    Window(
        Format("🔢 <b>Новый номер для {selected_season}-го сезона:</b>"),
        MessageInput(on_edit_season_num, content_types=ContentType.TEXT),
        SwitchTo(Const("⬅️ Назад"), id="b8", state=EditMovieSG.select_episode),
        state=EditMovieSG.edit_global_season,
        getter=get_season_data,
    ),
    Window(
        DynamicMedia("media", when="is_film"),
        Format("⚠️ <b>УДАЛИТЬ ПОЛНОСТЬЮ?</b>\n\n«{name}» (ID: {code})?"),
        Button(Const("✅ Да, удалить"), id="cd", on_click=on_delete_confirm),
        SwitchTo(Const("❌ Нет"), id="cn", state=EditMovieSG.select_action),
        state=EditMovieSG.confirm_delete,
        getter=get_movie_info,
    ),
    Window(
        DynamicMedia("media"),
        Multi(
            Format("⚠️ <b>Удалить С{selected_ep[season]} Э{selected_ep[episode]}?</b>", when="is_series"),
            Format("⚠️ <b>Удалить Серию {selected_ep[episode]}?</b>", when="is_mini_series")
        ),
        Button(Const("✅ Да, удалить"), id="ce", on_click=on_delete_episode_confirm),
        SwitchTo(Const("❌ Нет"), id="cn2", state=EditMovieSG.edit_episode_details),
        state=EditMovieSG.confirm_delete_episode,
        getter=get_movie_info,
    ),
    Window(
        Format("⚠️ <b>Удалить весь {selected_season}-й сезон?</b>"),
        Button(Const("✅ Да, удалить"), id="cs", on_click=on_delete_season_confirm),
        SwitchTo(Const("❌ Нет"), id="cn3", state=EditMovieSG.select_episode),
        state=EditMovieSG.confirm_delete_season,
        getter=get_season_data,
    ),
    Window(
        Format("🎭 <b>Жанры для «{name}»:</b>\n"
               "<i>(Выберите для изменения)</i>\n\n"
               "<b>Выбрано:</b> {selected_text}"),
        Group(
            Select(
                Format("{item[1]}"),
                id="g_select_edit",
                item_id_getter=lambda x: x[0],
                items="genres",
                on_click=on_genre_toggle,
            ),
            id="g_group_edit",
            width=2,
        ),
        Button(Const("✅ Сохранить"), id="save_genres", on_click=on_genre_toggle),
        Button(Const("⬅️ Назад"), id="back_to_prev_from_genres", on_click=on_back_click),
        state=EditMovieSG.edit_genres,
        getter=get_genre_data,
    ),
)
