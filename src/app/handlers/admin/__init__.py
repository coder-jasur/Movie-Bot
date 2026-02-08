from aiogram import Router, F

from src.app.core.config import Settings
from src.app.dialog.admin import admin_main_dialog, add_movie_dialog, edit_movie_dialog, backup_dialog
from src.app.dialog.admin.referral import referral_dialog
from src.app.dialog.dialogs import op_management_dialog, channel_management_dialog, bot_management_dialog, add_channel_dialog, add_bot_dialog
from src.app.handlers.admin.commands import admin_commands_router
from src.app.handlers.admin.mandatory_subs import mandatory_subs_router
from src.app.handlers.admin.check import check_sub_router


def register_admin_routers(router: Router, settings: Settings):
    admins_id = []
    for admin in settings.admins_ids:
        admins_id.append(int(admin))
    admin_register_router = Router()
    admin_register_router.message.filter(F.from_user.id.in_(admins_id))
    admin_register_router.callback_query.filter(F.from_user.id.in_(admins_id))

    # Admin command handlers
    admin_register_router.include_router(admin_commands_router)
    admin_register_router.include_router(mandatory_subs_router)
    admin_register_router.include_router(check_sub_router)

    # Admin dialogs
    admin_register_router.include_router(admin_main_dialog)
    admin_register_router.include_router(add_movie_dialog)
    admin_register_router.include_router(edit_movie_dialog)
    admin_register_router.include_router(referral_dialog)
    admin_register_router.include_router(backup_dialog)
    
    # Channel/Bot management dialogs (OP Menu)
    admin_register_router.include_router(op_management_dialog)
    admin_register_router.include_router(channel_management_dialog)
    admin_register_router.include_router(bot_management_dialog)
    admin_register_router.include_router(add_channel_dialog)
    admin_register_router.include_router(add_bot_dialog)
    
    router.include_router(admin_register_router)
