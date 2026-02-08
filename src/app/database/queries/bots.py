from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.models import Bot


class BotActions:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_bot(
            self,
            bot_name: str,
            bot_username: str,
            bot_url: str,
            bot_status: str = "True",
    ):
        bot = Bot(
            bot_name=bot_name,
            bot_username=bot_username,
            bot_url=bot_url,
            bot_status=bot_status
        )
        self.session.add(bot)
        await self.session.commit()

    async def get_bot(self, bot_username: str):
        stmt = select(Bot).where(Bot.bot_username == bot_username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_bots(self):
        stmt = select(Bot)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_bot_status(self, new_bot_status: str, bot_username: str):
        stmt = update(Bot).where(Bot.bot_username == bot_username).values(bot_status=new_bot_status)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_bot(self, bot_username: str):
        stmt = delete(Bot).where(Bot.bot_username == bot_username)
        await self.session.execute(stmt)
        await self.session.commit()
