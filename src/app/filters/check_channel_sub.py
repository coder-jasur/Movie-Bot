from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.queries.channels import ChannelActions


class CheckSubscription(BaseFilter):
    _channels_cache = []
    _last_update = None
    _cache_ttl = timedelta(minutes=5)

    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession, bot: Bot, **kwargs):
        # Only check subscription in private chats
        if isinstance(event, Message):
            if event.chat.type != ChatType.PRIVATE:
                return False
            # Ignore /start command
            if event.text and event.text.startswith("/start"):
                return False
        elif isinstance(event, CallbackQuery):
            if event.message.chat.type != ChatType.PRIVATE:
                return False

        # Cache logic to prevent DB spam on every message
        now = datetime.now()
        if not self._last_update or (now - self._last_update) > self._cache_ttl:
            channel_actions = ChannelActions(session)
            self._channels_cache = await channel_actions.get_all_channels()
            self._last_update = now
        
        channel_data = self._channels_cache

        if not channel_data:
            return False

        for channel in channel_data:
            # Check for string "True" or boolean True just in case
            if channel.channel_status == "True" or channel.channel_status is True:
                try:
                    user_status = await bot.get_chat_member(channel.channel_id, event.from_user.id)
                    if user_status.status not in ["member", "administrator", "creator"]:
                        return True
                except Exception:
                    # Ignore errors, maybe channel not found or bot kicked
                    continue
        return False
