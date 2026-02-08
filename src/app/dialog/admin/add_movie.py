from typing import Any
import html

from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.kbd import Button, Row, SwitchTo, Back, Start, Next, Cancel, Column, Select, ScrollingGroup, \
    Group
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Const, Format, Case, Multi
from aiogram_dialog.widgets.input import MessageInput
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.queries.movie.feature_films import FeatureFilmsActions
from src.app.database.queries.movie.series import SeriesActions
from src.app.database.queries.movie.mini_series import MiniSeriesActions
from src.app.states.admin.dialogs import AddMovieWizardSG, AdminMenuSG
from src.app.common.genres import serialize_genres, deserialize_genres, get_genre_display_text


# --- Handlers ---

async def on_movie_type_selected(c: CallbackQuery, widget: Button, manager: DialogManager):
    manager.dialog_data["movie_type"] = widget.widget_id
    await manager.next()


async def on_code_input(m: Message, widget: Any, manager: DialogManager):
    if not m.text.isdigit():
        await m.answer("❌ Используйте только цифры!")
        return

    code = int(m.text)
    manager.dialog_data["code"] = code
    session: AsyncSession = manager.middleware_data["session"]

    # Check if code exists
    ff = await FeatureFilmsActions(session).get_feature_film(code)
    if ff:
        manager.dialog_data["exists"] = True
        manager.dialog_data["exist_type"] = "feature_film"
        manager.dialog_data["name"] = ff.name
        await manager.switch_to(AddMovieWizardSG.quick_add)
        return

    s = await SeriesActions(session).get_series(code)
    if s:
        manager.dialog_data["exists"] = True
        manager.dialog_data["exist_type"] = "series"
        manager.dialog_data["name"] = s[0].name
        # Load existing genres for series
        if s[0].genres:
            manager.dialog_data["genres"] = deserialize_genres(s[0].genres)
        await manager.switch_to(AddMovieWizardSG.quick_add)
        return

    ms = await MiniSeriesActions(session).get_mini_series(code)
    if ms:
        manager.dialog_data["exists"] = True
        manager.dialog_data["exist_type"] = "mini_series"
        manager.dialog_data["name"] = ms[0].name
        # Load existing genres for mini-series
        if ms[0].genres:
            manager.dialog_data["genres"] = deserialize_genres(ms[0].genres)
        await manager.switch_to(AddMovieWizardSG.quick_add)
        return

    await manager.switch_to(AddMovieWizardSG.input_name)


async def on_quick_next(c: CallbackQuery, widget: Any, manager: DialogManager):
    """Continuing addition for an existing series/mini-series code."""
    # Reset episode-specific data but keep global ones
    keys_to_reset = ["name", "series", "season", "file_id", "caption", "exists", "exist_type", "genres_exist"]
    for key in keys_to_reset:
        manager.dialog_data.pop(key, None)
    
    await c.answer()
    await manager.switch_to(AddMovieWizardSG.input_name)


async def on_quick_new_season(c: CallbackQuery, widget: Any, manager: DialogManager):
    await manager.switch_to(AddMovieWizardSG.input_season_number)


async def on_quick_edit(c: CallbackQuery, widget: Any, manager: DialogManager):
    pass  # To be implemented if needed


async def on_name_input(m: Message, widget: Any, manager: DialogManager):
    manager.dialog_data["name"] = m.text
    session: AsyncSession = manager.middleware_data["session"]
    code = manager.dialog_data.get("code")
    movie_type = manager.dialog_data.get("movie_type")
    
    # For series/mini-series, check if genres already exist (continuing existing series)
    genres_exist = False
    if movie_type == "series":
        existing = await SeriesActions(session).get_series(code)
        if existing and existing[0].genres:
            manager.dialog_data["genres"] = deserialize_genres(existing[0].genres)
            genres_exist = True
    elif movie_type == "mini_series":
        existing = await MiniSeriesActions(session).get_mini_series(code)
        if existing and existing[0].genres:
            manager.dialog_data["genres"] = deserialize_genres(existing[0].genres)
            genres_exist = True
    
    # If genres are already known, skip genre selection
    if genres_exist:
        if movie_type == "series":
            await manager.switch_to(AddMovieWizardSG.input_season_number)
        elif movie_type == "mini_series":
            await manager.switch_to(AddMovieWizardSG.input_series_number)
        else:
            await manager.switch_to(AddMovieWizardSG.input_file)
    # If it's a series type but genres are missing, go select them
    elif movie_type in ["series", "mini_series"]:
        if "genres" not in manager.dialog_data:
            manager.dialog_data["genres"] = []
        await manager.switch_to(AddMovieWizardSG.select_genres)
    # For films, genres are asked later in the flow (after caption)
    else:
        await manager.switch_to(AddMovieWizardSG.input_file)


async def on_season_input(m: Message, widget: Any, manager: DialogManager):
    if not m.text.isdigit():
        await m.answer("❌ Введите число!")
        return
    manager.dialog_data["season"] = int(m.text)
    await manager.switch_to(AddMovieWizardSG.input_series_number)


async def on_series_num_input(m: Message, widget: Any, manager: DialogManager):
    if not m.text.isdigit():
        await m.answer("❌ Введите число!")
        return

    num = int(m.text)
    code = manager.dialog_data.get("code")
    m_type = manager.dialog_data.get("movie_type")
    session: AsyncSession = manager.middleware_data["session"]

    # Check if episode exists
    if m_type == "series":
        season = manager.dialog_data.get("season")
        eps = await SeriesActions(session).get_series(code)
        if any(e.season == season and e.series == num for e in eps):
            await m.answer(f"⚠️ Сезон {season}, серия {num} уже существует!")
            return
    elif m_type == "mini_series":
        eps = await MiniSeriesActions(session).get_mini_series(code)
        if any(e.series == num for e in eps):
            await m.answer(f"⚠️ Серия {num} уже существует!")
            return

    manager.dialog_data["series"] = num
    await manager.switch_to(AddMovieWizardSG.input_file)


async def on_file_input(m: Message, widget: Any, manager: DialogManager):
    if m.video:
        manager.dialog_data["file_id"] = m.video.file_id
    elif m.document:
        manager.dialog_data["file_id"] = m.document.file_id
    else:
        await m.answer("❌ Пожалуйста, отправьте видео или файл!")
        return
    await manager.switch_to(AddMovieWizardSG.input_caption)


async def on_caption_input(m: Message, widget: Any, manager: DialogManager):
    manager.dialog_data["caption"] = m.html_text if m.caption else m.text
    movie_type = manager.dialog_data.get("movie_type")
    
    # For feature films, show genre selection after caption
    if movie_type == "feature_film":
        if "genres" not in manager.dialog_data:
            manager.dialog_data["genres"] = []
        await manager.switch_to(AddMovieWizardSG.select_genres)
    else:
        await manager.switch_to(AddMovieWizardSG.confirm)


async def on_skip_caption(c: CallbackQuery, widget: Any, manager: DialogManager):
    manager.dialog_data["caption"] = None
    movie_type = manager.dialog_data.get("movie_type")
    
    # For feature films, show genre selection after skipping caption
    if movie_type == "feature_film":
        if "genres" not in manager.dialog_data:
            manager.dialog_data["genres"] = []
        await manager.switch_to(AddMovieWizardSG.select_genres)
    else:
        await manager.switch_to(AddMovieWizardSG.confirm)


async def on_genre_toggle(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str = None):
    """Handle genre button toggle (add/remove from selection) and confirmation."""
    
    # If it's the confirm button
    if widget.widget_id == "confirm_genres":
        # Check if we were editing
        if manager.dialog_data.get("editing_field") == "e_genres":
            # Clear the editing field flag and return to confirm
            manager.dialog_data.pop("editing_field", None)
            await manager.switch_to(AddMovieWizardSG.confirm)
            return

        m_type = manager.dialog_data.get("movie_type")
        if m_type == "series":
            await manager.switch_to(AddMovieWizardSG.input_season_number)
        elif m_type == "mini_series":
            await manager.switch_to(AddMovieWizardSG.input_series_number)
        else:
            await manager.switch_to(AddMovieWizardSG.confirm)
        return
    
    # Otherwise it's the Select widget passing item_id
    genre_name = item_id
    if not genre_name:
        return
    
    # Use a list copy to ensure aiogram-dialog detects the change
    selected = list(manager.dialog_data.get("genres", []))
    if genre_name in selected: 
        selected.remove(genre_name)
    else: 
        selected.append(genre_name)
    manager.dialog_data["genres"] = selected
    await c.answer()


async def on_confirm(c: CallbackQuery, widget: Any, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    data = manager.dialog_data
    m_type = data.get("movie_type")

    try:
        if m_type == "feature_film":
            await FeatureFilmsActions(session).add_feature_film(
                film_code=data["code"],
                film_name=data["name"],
                video_file_id=data["file_id"],
                caption=data.get("caption"),
                genres=serialize_genres(data.get("genres", []))
            )
        elif m_type == "series":
            await SeriesActions(session).add_series(
                series_code=data["code"],
                series_name=data["name"],
                series_num=data["series"],
                season=data["season"],
                video_file_id=data["file_id"],
                caption=data.get("caption"),
                genres=serialize_genres(data.get("genres", []))
            )
        elif m_type == "mini_series":
            await MiniSeriesActions(session).add_mini_series(
                mini_series_code=data["code"],
                mini_series_name=data["name"],
                series=data["series"],
                video_file_id=data["file_id"],
                caption=data.get("caption"),
                genres=serialize_genres(data.get("genres", []))
            )

        await c.message.answer("✅ Успешно сохранено!")
        await manager.switch_to(AddMovieWizardSG.success)
    except Exception as e:
        await c.message.answer(f"❌ Ошибка: {html.escape(str(e))}")


async def on_edit_click(c: CallbackQuery, widget: Any, manager: DialogManager):
    await manager.switch_to(AddMovieWizardSG.edit_menu)


async def on_edit_field_selected(c: CallbackQuery, widget: Button, manager: DialogManager):
    manager.dialog_data["editing_field"] = widget.widget_id
    if widget.widget_id == "e_genres":
        await manager.switch_to(AddMovieWizardSG.select_genres)
    else:
        await manager.switch_to(AddMovieWizardSG.edit_field)


async def on_field_edit_input(m: Message, widget: Any, manager: DialogManager):
    field = manager.dialog_data.get("editing_field")
    session: AsyncSession = manager.middleware_data["session"]

    if field == "e_code":
        if not m.text.isdigit():
            await m.answer("❌ Код должен состоять только из цифр!")
            return

        new_code = int(m.text)

        # Проверяем, занят ли код другими фильмами
        ff = await FeatureFilmsActions(session).get_feature_film(new_code)
        s = await SeriesActions(session).get_series(new_code)
        ms = await MiniSeriesActions(session).get_mini_series(new_code)

        if ff or s or ms:
            await m.answer("⚠️ Этот код уже занят. Пожалуйста, выберите другой!")
            return

        manager.dialog_data["code"] = new_code

    elif field == "e_name":
        manager.dialog_data["name"] = m.text

    elif field == "e_caption":
        manager.dialog_data["caption"] = m.html_text if m.caption else m.text

    elif field == "e_video" and (m.video or m.document):
        manager.dialog_data["file_id"] = m.video.file_id if m.video else m.document.file_id

    elif field == "e_season" and m.text.isdigit():
        new_season = int(m.text)
        code = manager.dialog_data.get("code")
        m_type = manager.dialog_data.get("movie_type")
        if m_type == "series":
            eps = await SeriesActions(session).get_series(code)
            current_series = manager.dialog_data.get("series")
            if any(e.season == new_season and e.series == current_series for e in eps):
                await m.answer(f"⚠️ Сезон {new_season}, серия {current_series} уже существует!")
                return
        manager.dialog_data["season"] = new_season

    elif field == "e_series" and m.text.isdigit():
        new_series = int(m.text)
        code = manager.dialog_data.get("code")
        m_type = manager.dialog_data.get("movie_type")
        if m_type == "series":
            season = manager.dialog_data.get("season")
            eps = await SeriesActions(session).get_series(code)
            if any(e.season == season and e.series == new_series for e in eps):
                await m.answer(f"⚠️ Сезон {season}, серия {new_series} уже существует!")
                return
        elif m_type == "mini_series":
            eps = await MiniSeriesActions(session).get_mini_series(code)
            if any(e.series == new_series for e in eps):
                await m.answer(f"⚠️ Серия {new_series} уже существует!")
                return
        manager.dialog_data["series"] = new_series

    await manager.switch_to(AddMovieWizardSG.confirm)



async def on_finish(c: CallbackQuery, widget: Any, manager: DialogManager):
    await manager.done()


async def on_add_more(c: CallbackQuery, widget: Any, manager: DialogManager):
    """Adding another episode/part in the success loop."""
    # Reset episode-specific data but keep global ones (movie_type, code, genres)
    keys_to_reset = ["name", "series", "season", "file_id", "caption", "editing_field"]
    for key in keys_to_reset:
        manager.dialog_data.pop(key, None)

    await c.answer()
    await manager.switch_to(AddMovieWizardSG.input_name)


async def on_back_to_type(c: CallbackQuery, widget: Any, manager: DialogManager):
    await manager.switch_to(AddMovieWizardSG.choose_type)


async def on_finish_to_admin(c: CallbackQuery, widget: Any, manager: DialogManager):
    await manager.done()


async def on_cancel_to_type(c: CallbackQuery, widget: Any, manager: DialogManager):
    await manager.switch_to(AddMovieWizardSG.choose_type)


# --- Getters ---

async def get_genre_data(dialog_manager: DialogManager, **kwargs):
    """Getter for genre selection window - provides the genres and selection state."""
    from src.app.common.genres import GENRES
    selected_genres = dialog_manager.dialog_data.get("genres", [])
    
    # Create list of tuples (name, display_with_checkmark)
    genre_list = []
    for g in GENRES:
        name = g["name"]
        checkmark = "✓ " if name in selected_genres else ""
        genre_list.append((name, f"{checkmark}{g['display']}")) # Use 'display' for Russian
    
    return {
        "name": dialog_manager.dialog_data.get("name"),
        "genres": genre_list,
        "selected_text": get_genre_display_text(selected_genres, lang="ru")
    }


async def get_edit_data(dialog_manager: DialogManager, **kwargs):
    """Геттер для редактирования поля - БЕЗ МЕДИА"""
    field = dialog_manager.dialog_data.get("editing_field")
    prompts = {
        "e_code": "🔢 Введите новый код (ID):",
        "e_name": "📛 Введите новое название:",
        "e_caption": "📄 Введите новое описание:",
        "e_video": "📹 Отправьте новый видео файл:",
        "e_season": "📅 Введите новый номер сезона:",
        "e_series": "🔢 Введите новый номер серии:"
    }

    return {
        "prompt": prompts.get(field, "Введите изменение:")
    }


async def get_quick_add_data(dialog_manager: DialogManager, **kwargs):
    d = dialog_manager.dialog_data
    m_type = d.get("movie_type")
    e_type = d.get("exist_type")

    can_continue = (m_type == "series" and e_type == "series") or (m_type == "mini_series" and e_type == "mini_series")

    types = {"feature_film": "Фильм", "series": "Сериал", "mini_series": "Мини-сериал"}

    text = "Этот код занят. "
    if can_continue:
        text += "Но он совпадает с этим типом. Вы можете продолжить, чтобы добавить новую серию."
    else:
        text += "Он принадлежит другому типу или фильму. Вы не можете использовать его здесь."

    return {
        "display_type": types.get(e_type, e_type),
        "name": d.get("name"),
        "can_continue": can_continue,
        "can_continue_text": text
    }


async def get_success_data(dialog_manager: DialogManager, **kwargs):
    return {
        "is_not_film": dialog_manager.dialog_data.get("movie_type") != "feature_film"
    }


async def get_summary(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.dialog_data
    m_type = data.get("movie_type")
    types = {"feature_film": "🎬 Фильм", "series": "📺 Сериал", "mini_series": "🧩 Мини-сериал"}

    summary = f"📑 <b>ИТОГ:</b>\n━━━━━━━━━━━━━━━\n"
    summary += f"<b>📂 Тип:</b> {types.get(m_type)}\n"
    summary += f"<b>🔢 Код:</b> <code>{data.get('code')}</code>\n"
    summary += f"<b>🎬 Название:</b> {data.get('name')}\n"
    summary += f"<b>🎭 Жанры:</b> {get_genre_display_text(data.get('genres', []), lang='ru')}\n"

    if m_type == "series":
        summary += f"<b>📅 Сезон:</b> {data.get('season')}\n"
        summary += f"<b>🔢 Серия:</b> {data.get('series')}\n"
    elif m_type == "mini_series":
        summary += f"<b>🔢 Серия:</b> {data.get('series')}\n"

    summary += f"\n<b>📄 Описание:</b>\n{data.get('caption')}" if data.get('caption') else "\n<b>📄 Описание:</b> Нет"
    summary += f"\n━━━━━━━━━━━━━━━"

    file_id = data.get("file_id")
    media = None
    if file_id:
        media = MediaAttachment(type=ContentType.VIDEO, file_id=MediaId(file_id))

    return {
        "summary": summary,
        "media": media,
        "is_series": m_type == "series",
        "is_mini": m_type == "mini_series",
        "is_not_film": m_type in ["series", "mini_series"]
    }
# --- Dialog ---

add_movie_dialog = Dialog(
    Window(
        Const("🎬 <b>Выберите тип контента:</b>"),
        Column(
            Button(Const("🎞 Фильм"), id="feature_film", on_click=on_movie_type_selected),
            Button(Const("📺 Сериал"), id="series", on_click=on_movie_type_selected),
            Button(Const("🧩 Мини-сериал"), id="mini_series", on_click=on_movie_type_selected),
        ),
        Cancel(Const("🏠 Админ меню"), id="cancel_to_admin"),
        state=AddMovieWizardSG.choose_type,
    ),
    Window(
        Const("🔢 <b>Введите код (ID):</b>\n(Только цифры)"),
        MessageInput(on_code_input, content_types=ContentType.TEXT),
        SwitchTo(Const("🔙 Назад"), id="back_to_type", state=AddMovieWizardSG.choose_type),
        state=AddMovieWizardSG.input_code,
    ),
    Window(
        Format("🔍 <b>Код занят!</b>\n\n"
               "📂 <b>Тип:</b> {display_type}\n"
               "🎬 <b>Название:</b> {name}\n\n"
               "{can_continue_text}"),
        Button(Const("✅ Продолжить"), id="q_next", when="can_continue", on_click=on_quick_next),
        SwitchTo(Const("🔙 Назад"), id="back_to_code", state=AddMovieWizardSG.input_code),
        state=AddMovieWizardSG.quick_add,
        getter=get_quick_add_data,
    ),
    Window(
        Const("📝 <b>Введите название:</b>"),
        MessageInput(on_name_input, content_types=ContentType.TEXT),
        Row(
            SwitchTo(Const("🔙 Назад"), id="back_to_code_manual", state=AddMovieWizardSG.input_code),
            Button(Const("❌ Отмена"), id="cancel_to_type_name", on_click=on_cancel_to_type),
        ),
        state=AddMovieWizardSG.input_name,
    ),
    Window(
        Const("🔢 <b>Введите номер сезона:</b>"),
        MessageInput(on_season_input, content_types=ContentType.TEXT),
        Row(
            SwitchTo(Const("🔙 Назад"), id="back_to_name_s", state=AddMovieWizardSG.input_name),
            Button(Const("❌ Отмена"), id="cancel_to_type_s", on_click=on_cancel_to_type),
        ),
        state=AddMovieWizardSG.input_season_number,
    ),
    Window(
        Const("🔢 <b>Введите номер серии:</b>"),
        MessageInput(on_series_num_input, content_types=ContentType.TEXT),
        Row(
            SwitchTo(Const("🔙 Назад"), id="back_to_season_s", state=AddMovieWizardSG.input_season_number),
            Button(Const("❌ Отмена"), id="cancel_to_type_ep", on_click=on_cancel_to_type),
        ),
        state=AddMovieWizardSG.input_series_number,
    ),
    Window(
        Const("📹 <b>Отправьте видео файл:</b>"),
        MessageInput(on_file_input, content_types=[ContentType.VIDEO, ContentType.DOCUMENT]),
        Row(
            SwitchTo(Const("🔙 Назад"), id="back_to_prev_f", state=AddMovieWizardSG.input_name),
            Button(Const("❌ Отмена"), id="cancel_to_type_f", on_click=on_cancel_to_type),
        ),
        state=AddMovieWizardSG.input_file,
    ),
    Window(
        Const("📄 <b>Введите описание:</b>"),
        MessageInput(on_caption_input, content_types=ContentType.TEXT),
        Button(Const("➡️ Пропустить"), id="skip_caption", on_click=on_skip_caption),
        Row(
            SwitchTo(Const("🔙 Назад"), id="back_to_file", state=AddMovieWizardSG.input_file),
            Button(Const("❌ Отмена"), id="cancel_to_type_c", on_click=on_cancel_to_type),
        ),
        state=AddMovieWizardSG.input_caption,
    ),
    Window(
        Format("🎭 <b>Выберите жанры:</b>\n"
               "<i>(Можно выбрать несколько)</i>\n\n"
               "<b>Выбрано:</b> {selected_text}"),
        Group(
            Select(
                Format("{item[1]}"),
                id="g_select",
                item_id_getter=lambda x: x[0],
                items="genres",
                on_click=on_genre_toggle,
            ),
            id="g_group",
            width=2,
        ),
        Button(Const("✅ Сохранить (Завершить)"), id="confirm_genres", on_click=on_genre_toggle),
        Row(
            SwitchTo(Const("🔙 Вернуться к итогу"), id="back_to_confirm", state=AddMovieWizardSG.confirm, when=lambda d, w, m: m.dialog_data.get("editing_field") == "e_genres"),
            SwitchTo(Const("🔙 Назад"), id="back_to_caption", state=AddMovieWizardSG.input_caption, when=lambda d, w, m: m.dialog_data.get("editing_field") != "e_genres"),
        ),
        state=AddMovieWizardSG.select_genres,
        getter=get_genre_data,
    ),
    Window(
        DynamicMedia("media"),
        Format("{summary}"),
        Row(
            Button(Const("✅ Сохранить"), id="save", on_click=on_confirm),
            Button(Const("✏️ Изменить"), id="edit", on_click=on_edit_click),
        ),
        Button(Const("❌ Отмена"), id="cancel_to_type_final", on_click=on_cancel_to_type),
        state=AddMovieWizardSG.confirm,
        getter=get_summary,
    ),
    Window(
        DynamicMedia("media"),
        Format("{summary}"),
        Const("\n🛠 <b>Что изменить?</b>"),
        Column(
            Button(Const("🔢 Код (ID)"), id="e_code", on_click=on_edit_field_selected),
            Button(Const("📛 Название"), id="e_name", on_click=on_edit_field_selected),
            Button(Const("🎭 Жанры"), id="e_genres", on_click=on_edit_field_selected),
            Button(Const("📄 Описание"), id="e_caption", on_click=on_edit_field_selected),
            Button(Const("📹 Видео"), id="e_video", on_click=on_edit_field_selected),
            Button(Const("📅 Сезон"), id="e_season", on_click=on_edit_field_selected, when="is_series"),
            Button(Const("🔢 Серия"), id="e_series", on_click=on_edit_field_selected, when="is_not_film"),
        ),
        SwitchTo(Const("✅ Готово / Сохранить"), id="back_to_hub_save", state=AddMovieWizardSG.confirm),
        SwitchTo(Const("🔙 Назад"), id="back_to_confirm", state=AddMovieWizardSG.confirm),
        state=AddMovieWizardSG.edit_menu,
        getter=get_summary,
    ),
    Window(
        Format("{prompt}"),
        MessageInput(on_field_edit_input),
        SwitchTo(Const("🔙 Назад"), id="back_to_edit_menu", state=AddMovieWizardSG.edit_menu),
        state=AddMovieWizardSG.edit_field,
        getter=get_edit_data,
    ),
    Window(
        Const("✅ <b>Успешно сохранено!</b>\n\nЧто делаем дальше?"),
        Column(
            Button(Const("➕ Продолжить"), id="continue_loop", on_click=on_add_more, when="is_not_film"),
            Button(Const("🔙 Назад"), id="back_type", on_click=on_back_to_type),
            Button(Const("🏠 Главное меню"), id="finish_admin", on_click=on_finish_to_admin),
        ),
        state=AddMovieWizardSG.success,
        getter=get_success_data,
    ),
)
