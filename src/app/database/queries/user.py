from typing import AsyncGenerator

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.models import User


class UserActions:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_user(self, tg_id: int, username: str, status: str = "unblocked", language_code: str = None, is_premium: bool = False):
        user = User(
            tg_id=tg_id, 
            username=username, 
            status=status, 
            language_code=language_code, 
            is_premium=is_premium
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def get_user(self, tg_id: int):
        stmt = select(User).where(User.tg_id == tg_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_user(self):
        stmt = select(User)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_registration_stats(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        year_ago = now - timedelta(days=365)

        # Total
        stmt_total = select(func.count(User.tg_id))
        total = (await self.session.execute(stmt_total)).scalar()

        # Day
        stmt_day = select(func.count(User.tg_id)).where(User.created_at >= day_ago)
        day = (await self.session.execute(stmt_day)).scalar()

        # Month
        stmt_month = select(func.count(User.tg_id)).where(User.created_at >= month_ago)
        month = (await self.session.execute(stmt_month)).scalar()

        # Week
        stmt_week = select(func.count(User.tg_id)).where(User.created_at >= week_ago)
        week = (await self.session.execute(stmt_week)).scalar()

        # Year
        stmt_year = select(func.count(User.tg_id)).where(User.created_at >= year_ago)
        year = (await self.session.execute(stmt_year)).scalar()
        
        # New Stats: Premium & Language
        stmt_premium = select(func.count(User.tg_id)).where(User.is_premium == True)
        premium_count = (await self.session.execute(stmt_premium)).scalar()
        
        stmt_langs = select(User.language_code, func.count(User.tg_id)).group_by(User.language_code).order_by(func.count(User.tg_id).desc()).limit(5)
        langs_result = (await self.session.execute(stmt_langs)).all()
        langs_stats = [{"code": row[0] or "unknown", "count": row[1]} for row in langs_result]

        return {
            "total": total,
            "day": day,
            "week": week,
            "month": month,
            "year": year,
            "premium": premium_count,
            "languages": langs_stats
        }

    async def update_user_status(self, new_status: str, tg_id: int):
        stmt = update(User).where(User.tg_id == tg_id).values(status=new_status)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_user_ids_batch(self, offset: int, limit: int = 5000) -> list[int]:
        stmt = select(User.tg_id).order_by(User.tg_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def iterate_user_ids(
        self,
        batch_size: int = 5000
    ) -> AsyncGenerator[tuple[list[int], int], None]:

        offset = 0

        while True:
            user_ids = await self.get_user_ids_batch(offset, batch_size)

            if not user_ids:
                break

            yield user_ids, offset
            offset += len(user_ids)
