from typing import Sequence

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.app.database.models import FeatureFilm

logger = logging.getLogger(__name__)


class FeatureFilmsActions:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_feature_film(
            self,
            film_code: int,
            film_name: str,
            video_file_id: str,
            caption: str,
            genres: str = None,
    ):
        film = FeatureFilm(
            code=film_code,
            name=film_name,
            video_file_id=video_file_id,
            captions=caption,
            genres=genres
        )
        self.session.add(film)
        await self.session.commit()

    async def get_feature_film(self, film_code: int) -> FeatureFilm | None:
        try:
            stmt = select(FeatureFilm).where(FeatureFilm.code == film_code)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting feature film {film_code}: {e}")
            return None

    async def get_top_viewed_movies(self, limit: int = 20):
        stmt = select(FeatureFilm.code, FeatureFilm.views_count).order_by(FeatureFilm.views_count.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.all()

    async def increment_views(self, film_code: int):
        stmt = update(FeatureFilm).where(FeatureFilm.code == film_code).values(views_count=FeatureFilm.views_count + 1)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_feature_film(self, film_code: int):
        stmt = delete(FeatureFilm).where(FeatureFilm.code == film_code)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_all_feature_films(self) -> Sequence[FeatureFilm]:

        stmt = select(FeatureFilm)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_feature_film(self, film_code: int, **values):
        stmt = update(FeatureFilm).where(FeatureFilm.code == film_code).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_genres(self, film_code: int, genres: str) -> None:
        """Update genres for a feature film."""
        stmt = update(FeatureFilm).where(FeatureFilm.code == film_code).values(genres=genres)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_movie_code(self, old_code: int, new_code: int) -> None:
        """
        Update the movie code.
        """
        # Check if new code exists
        existing = await self.get_feature_film(new_code)
        if existing:
            raise ValueError(f"Code {new_code} already exists")

        stmt = (
            update(FeatureFilm)
            .where(FeatureFilm.code == old_code)
            .values(code=new_code)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_random_feature_film(self) -> FeatureFilm | None:
        """
        Get one random feature film from database.
        """
        try:
            stmt = select(FeatureFilm).order_by(func.random()).limit(1)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting random feature film: {e}")
            return None