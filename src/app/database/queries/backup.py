from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.database.models import User, FeatureFilm, Series, MiniSeries, Favorite

class BackupQueries:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.created_at.asc()))
        return list(result.scalars().all())

    async def get_all_feature_films(self) -> list[FeatureFilm]:
        result = await self.session.execute(select(FeatureFilm))
        return list(result.scalars().all())

    async def get_all_series(self) -> list[Series]:
        result = await self.session.execute(select(Series))
        return list(result.scalars().all())

    async def get_all_mini_series(self) -> list[MiniSeries]:
        result = await self.session.execute(select(MiniSeries))
        return list(result.scalars().all())

    async def get_all_favorites(self) -> list[Favorite]:
        result = await self.session.execute(select(Favorite))
        return list(result.scalars().all())
