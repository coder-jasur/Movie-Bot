from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, SwitchTo, Cancel, ScrollingGroup, Select
from aiogram_dialog.widgets.text import Const, Format
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.queries.referral import ReferralActions
from src.app.states.admin.referral import ReferralSG


async def get_referrals(dialog_manager: DialogManager, **kwargs):
    session: AsyncSession = dialog_manager.middleware_data["session"]
    actions = ReferralActions(session)
    referrals = await actions.get_all_referrals()
    return {
        "referrals": referrals
    }


async def on_referral_selected(c: CallbackQuery, widget, manager: DialogManager, item_id: str):
    manager.dialog_data["referral_id"] = int(item_id)
    await manager.switch_to(ReferralSG.view)


async def get_referral_details(dialog_manager: DialogManager, **kwargs):
    session: AsyncSession = dialog_manager.middleware_data["session"]
    bot: Bot = dialog_manager.middleware_data["bot"]
    referral_id = dialog_manager.dialog_data.get("referral_id")
    
    actions = ReferralActions(session)
    referral = await actions.get_referral(referral_id)
    
    if not referral:
        return {
            "referral": None,
            "bot_link": "N/A"
        }
    
    bot_info = await bot.get_me()
    bot_link = f"https://t.me/{bot_info.username}"
    
    return {
        "referral": referral,
        "bot_link": bot_link
    }


async def on_referral_created(message: Message, widget, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    actions = ReferralActions(session)
    await actions.create_referral(message.text)
    await message.answer("✅ Успешно создано!")
    await manager.switch_to(ReferralSG.menu)


async def on_referral_delete(c: CallbackQuery, widget, manager: DialogManager):
    session: AsyncSession = manager.middleware_data["session"]
    referral_id = manager.dialog_data.get("referral_id")
    actions = ReferralActions(session)
    await actions.delete_referral(referral_id)
    await c.answer("✅ Удалено")
    await manager.switch_to(ReferralSG.menu)


referral_dialog = Dialog(
    Window(
        Const("🔗 <b>Рефералы</b>\n\nВыберите из списка или создайте нового:"),
        ScrollingGroup(
            Select(
                Format("{item.name} | {item.joined_count}"),
                id="referral_select",
                item_id_getter=lambda x: x.referral_id,
                items="referrals",
                on_click=on_referral_selected,
            ),
            id="referrals_group",
            width=1,
            height=10,
            hide_pager=True,
        ),
        SwitchTo(Const("➕ Создать реферала"), id="add_ref", state=ReferralSG.add),
        Cancel(Const("⬅️ Назад"), id="back"),
        state=ReferralSG.menu,
        getter=get_referrals,
    ),
    Window(
        Const("✏️ <b>Новый реферал:</b>\n\nВведите название:"),
        MessageInput(on_referral_created, content_types=ContentType.TEXT),
        SwitchTo(Const("❌ Отмена"), id="cancel_add", state=ReferralSG.menu),
        state=ReferralSG.add,
    ),
    Window(
        Format("ℹ️ <b>Информация о реферале:</b>\n\n"
               "🆔 ID: {referral.referral_id}\n"
               "🏷 Название: {referral.name}\n"
               "👥 Приглашено: {referral.joined_count}\n"
               "📅 Создан: {referral.created_at}\n\n"
               "🔗 <b>Ссылка:</b>\n<code>{bot_link}?start=ref_{referral.referral_id}</code>"),
        Button(Const("🗑 Удалить"), id="delete_ref", on_click=on_referral_delete),
        SwitchTo(Const("⬅️ Назад"), id="back_list", state=ReferralSG.menu),
        state=ReferralSG.view,
        getter=get_referral_details,
    ),
)
