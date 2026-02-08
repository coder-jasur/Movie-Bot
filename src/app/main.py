import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram_dialog import setup_dialogs

from logs.logger_conf import setup_logging
from src.app.settings.bot_commands import create_bot_commands
from src.app.database.database_backup import daily_database_sender
from src.app.database.database_dsn import construct_postgresql_url
from src.app.core.config import Settings
from src.app.database.core import Database, Base
from src.app.handlers import register_all_routers
from src.app.middleware import register_middleware


async def main():
    settings = Settings()

    dp = Dispatcher()

    dsn = construct_postgresql_url(settings)

    db = Database(dsn)

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    register_all_routers(dp, settings)
    setup_dialogs(dp)

    register_middleware(dp, db.session_factory)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))

    asyncio.create_task(daily_database_sender(bot, settings.admins_ids, db.session_factory))

    await create_bot_commands(bot, settings)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        setup_logging("logs/logger.yml")

        asyncio.run(main())
    except Exception as e:
        print("ERROR", e)
