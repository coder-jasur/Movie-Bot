from aiogram import Bot
import html
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Start, SwitchTo, Cancel
from aiogram_dialog.widgets.text import Const, Format
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.states.admin.dialogs import AdminMenuSG, AddMovieWizardSG, EditMovieSG, BackupSG
from src.app.states.admin.referral import ReferralSG
from src.app.states.admin.channel import OPMenu
from src.app.database.queries.user import UserActions
from src.app.services.broadcaster import Broadcaster



def get_flag_emoji(lang_code: str) -> str:
    """Return flag emoji for a language code."""
    flags = {
        "en": "🇺🇸", "ru": "🇷🇺", "uz": "🇺🇿", "kz": "🇰🇿", "uk": "🇺🇦",
        "de": "🇩🇪", "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹", "tr": "🇹🇷",
        "ar": "🇦🇪", "fa": "🇮🇷", "hi": "🇮🇳", "zh": "🇨🇳", "ja": "🇯🇵",
    }
    # Handle variations like en-US, ru-RU
    if not lang_code:
        return "🏳️"
    
    code = lang_code.split("-")[0].lower()
    return flags.get(code, "🏳️")


async def get_statistics(dialog_manager: DialogManager, **kwargs):
    session: AsyncSession = dialog_manager.middleware_data["session"]
    user_actions = UserActions(session)
    stats = await user_actions.get_registration_stats()
    
    # Format languages
    langs_str = "\n".join([f"   • {get_flag_emoji(l['code'])}: {l['count']}" for l in stats["languages"]])
    
    return {
        "day": stats["day"],
        "week": stats["week"],
        "month": stats["month"],
        "year": stats["year"],
        "total": stats["total"],
        "premium": stats["premium"],
        "languages": langs_str if langs_str else "   • N/A"
    }


async def on_broadcast_message(m: Message, widget, manager: DialogManager):
    # Store message for broadcasting
    manager.dialog_data["broadcast_message"] = m
    await manager.switch_to(AdminMenuSG.broadcast_confirm)


async def on_broadcast_confirm(c: CallbackQuery, widget, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    bot: Bot = manager.middleware_data["bot"]
    broadcast_message = manager.dialog_data.get("broadcast_message")
    
    if not broadcast_message:
        await c.answer("❌ Сообщение не найдено")
        return
    
    try:
        broadcaster = Broadcaster(
            bot=bot,
            session=session,
            admin_id=c.from_user.id,
            broadcasting_message=broadcast_message
        )
        await c.message.answer("🚀 Рассылка началась...")
        await broadcaster.broadcast()
        await c.message.answer("✅ Рассылка завершена!")
        await manager.switch_to(AdminMenuSG.menu)
    except Exception as e:
        await c.message.answer(f"❌ Ошибка: {html.escape(str(e))}")


admin_main_dialog = Dialog(
    Window(
        Const("👨‍💻 <b>Админ Панель</b>\n\nВыберите раздел:"),
        Row(
            Start(Const("🎬 Добавить фильм"), id="add_movie", state=AddMovieWizardSG.choose_type),
            Start(Const("✏️ Редактировать/Удалить"), id="edit_movie", state=EditMovieSG.input_code),
        ),
        Row(
            Start(Const("📢 Каналы и Боты"), id="channels_bots", state=OPMenu.menu),
            SwitchTo(Const("📨 Рассылка"), id="broadcast", state=AdminMenuSG.broadcast_input),
        ),
        Row(
            Start(Const("🔗 Рефералы"), id="referrals", state=ReferralSG.menu),
        ),
        Row(
            SwitchTo(Const("📊 Статистика"), id="stats", state=AdminMenuSG.statistics),
            Start(Const("💾 Бэкап"), id="backup", state=BackupSG.menu),
        ),
        Row(
            Cancel(Const("❌ Закрыть"), id="close_admin"),
        ),
        state=AdminMenuSG.menu,
    ),

    Window(
        Format("📊 <b>Статистика:</b>\n\n"
               "📅 <b>Сегодня:</b> {day}\n"
               "📆 <b>Неделя:</b> {week}\n"
               "🗓 <b>Месяц:</b> {month}\n"
               "📅 <b>Год:</b> {year}\n"
               "👥 <b>Всего:</b> {total}\n\n"
               "🌟 <b>Premium:</b> {premium}\n"
               "🌍 <b>Топ языков:</b>\n{languages}"),
        SwitchTo(Const("⬅️ Назад"), id="back_main", state=AdminMenuSG.menu),
        state=AdminMenuSG.statistics,
        getter=get_statistics,
    ),
    Window(
        Const("📨 <b>Рассылка</b>\n\nОтправьте сообщение, которое нужно разослать всем пользователям:"),
        MessageInput(on_broadcast_message, content_types=ContentType.ANY),
        SwitchTo(Const("❌ Отмена"), id="cancel_broadcast", state=AdminMenuSG.menu),
        state=AdminMenuSG.broadcast_input,
    ),
    Window(
        Const("⚠️ <b>Подтверждение рассылки</b>\n\nВы подтверждаете отправку сообщения?"),
        Button(Const("✅ Да, отправить"), id="confirm_broadcast", on_click=on_broadcast_confirm),
        SwitchTo(Const("❌ Отмена"), id="cancel_confirm", state=AdminMenuSG.menu),
        state=AdminMenuSG.broadcast_confirm,
    ),
)
