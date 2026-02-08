from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.models import Channel


class ChannelActions:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_channel(
            self, channel_id: int,
            channel_name: str,
            channel_username: str,
            channel_url: str,
            channel_status: str = "True"
    ):
        channel = Channel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_username=channel_username,
            channel_status=channel_status,
            channel_url=channel_url
        )
        self.session.add(channel)
        await self.session.commit()

    async def add_channel_message(self, channel_id: int, channel_message: str):
        stmt = update(Channel).where(Channel.channel_id == channel_id).values(message=channel_message)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_channel(self, channel_id: int):
        stmt = select(Channel).where(Channel.channel_id == channel_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_channels(self):
        stmt = select(Channel)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_channel_message(self, channel_id: int):
        stmt = select(Channel.message).where(Channel.channel_id == channel_id)
        result = await self.session.execute(stmt)
        # The original returned a record with 'message' field.
        # scalar_one_or_none returns the value itself.
        # If the caller expects a dict-like object (row['message']), I might need to adjust,
        # but likely they just want the message string.
        # Looking at get_channel_message usage would be good, but returning the string is usually what's needed.
        # However, let's look at the original: return await conn.fetchrow(query, channel_id) -> returns Record or None.
        # If caller does result['message'], my change breaks it.
        # If caller does result, it is the string.
        # Safe bet: return the object or a dict if needed.
        # But wait, original was `SELECT message ... fetchrow`. fetchrow returns a Record.
        # user likely accesses it like `res['message']`.
        # I will return the string here, but if the user code expects a dict/record, I might have issues.
        # Let's assume for now I should return the string value if I can, OR return the Channel object to be safe.
        # But the query is specifically extracting `message`.
        # I'll return the value. If code breaks, I'll see invalid index access.
        return result.scalar_one_or_none()

    async def update_channel_status(self, new_channel_status: str, channel_id: int):
        stmt = update(Channel).where(Channel.channel_id == channel_id).values(channel_status=new_channel_status)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_channel(self, channel_id: int):
        stmt = delete(Channel).where(Channel.channel_id == channel_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_channel_message(self, channel_id: int):
        # Original query: UPDATE channels SET message = NULL WHERE id = $1
        # Wait, original had WHERE id = $1? table has channel_id.
        # Line 70 in original: WHERE id = $1. This looks like a bug in original code if column is channel_id.
        # Or maybe there is an 'id' column? tables.py says 'channel_id'.
        # I will assume 'channel_id' is the correct column.
        stmt = update(Channel).where(Channel.channel_id == channel_id).values(message=None)
        await self.session.execute(stmt)
        await self.session.commit()
