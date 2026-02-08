from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.queries.user import UserActions
from src.app.database.queries.referral import ReferralActions
from src.app.keyboards.replay import random_movies

start_router = Router()


@start_router.message(CommandStart())
async def start_bot(message: Message, command: CommandStart, session: AsyncSession):
    user_actions = UserActions(session)
    referral_actions = ReferralActions(session)

    # Получение данных пользователя
    user_data = await user_actions.get_user(message.from_user.id)

    # Если пользователя нет — добавляем
    if not user_data:
        await user_actions.add_user(
            tg_id=message.from_user.id,
            username=message.from_user.username or message.from_user.first_name,
            language_code=message.from_user.language_code,
            is_premium=message.from_user.is_premium or False
        )
        
        # Проверка реферала (Checking referral)
        args = command.args
        if args and args.startswith("ref_"):
            try:
                referral_id = int(args.split("_")[1])
                await referral_actions.increment_joined_count(referral_id)
            except (ValueError, IndexError):
                pass

    # Определение имени пользователя
    name = (
        message.from_user.first_name
        or message.from_user.last_name
        or message.from_user.full_name
        or "Do'stim"
    )

    await message.answer(
        f"<b>👋 Salom {name}</b>\n\n"
        f"<b>Botimizga xush kelibsiz.</b>\n\n"
        f"<b>🍿 Kino kodini yuboring:</b>",
        reply_markup=random_movies
    )
