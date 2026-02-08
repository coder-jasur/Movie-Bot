from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.app.database.models import MiniSeries

logger = logging.getLogger(__name__)


class MiniSeriesActions:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_mini_series(
            self,
            mini_series_code: int,
            mini_series_name: str,
            series: int,
            video_file_id: str,
            caption: str,
            genres: str = None,
    ):
        ms = MiniSeries(
            code=mini_series_code,
            name=mini_series_name,
            series=series,
            video_file_id=video_file_id,
            captions=caption,
            genres=genres
        )
        # Update genres for all other episodes of the same mini-series
        if genres:
            stmt = update(MiniSeries).where(MiniSeries.code == mini_series_code).values(genres=genres)
            await self.session.execute(stmt)

        self.session.add(ms)
        await self.session.commit()

    async def get_mini_series(self, mini_series_code: int) -> list[MiniSeries]:
        try:
            stmt = select(MiniSeries).where(MiniSeries.code == mini_series_code).order_by(MiniSeries.series)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting mini series {mini_series_code}: {e}")
            return []

    async def delete_mini_series(self, mini_series_code: int):
        stmt = delete(MiniSeries).where(MiniSeries.code == mini_series_code)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_mini_series_for_series(self, mini_series_code: int, series: int):
        stmt = delete(MiniSeries).where(
            MiniSeries.code == mini_series_code,
            MiniSeries.series == series
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_all_mini_series(self) -> list[MiniSeries]:
        try:
            stmt = select(MiniSeries)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all mini series: {e}")
            return []

    async def update_mini_series(self, mini_series_code: int, **values):
        """Update metadata (Name/Caption) for ALL episodes of a mini-series code."""
        stmt = update(MiniSeries).where(MiniSeries.code == mini_series_code).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_episode_file(self, mini_series_code: int, series_num: int, file_id: str):
        """Update file_id for a specific episode."""
        stmt = update(MiniSeries).where(
            MiniSeries.code == mini_series_code,
            MiniSeries.series == series_num
        ).values(video_file_id=file_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_movie_code(self, old_code: int, new_code: int) -> None:
        """
        Update the mini-series code for all episodes.
        """
        # Check if new code exists
        existing = await self.get_mini_series(new_code)
        if existing:
            raise ValueError(f"Code {new_code} already exists")

        stmt = (
            update(MiniSeries)
            .where(MiniSeries.code == old_code)
            .values(code=new_code)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_episode_details(self, mini_series_code: int, old_series: int, **values):
        """
        Update specific episode details (series number).
        """
        stmt = update(MiniSeries).where(
            MiniSeries.code == mini_series_code,
            MiniSeries.series == old_series
        ).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_episode_metadata(self, mini_series_code: int, series_num: int, **values):
        """Update name/caption for a specific episode."""
        stmt = update(MiniSeries).where(
            MiniSeries.code == mini_series_code,
            MiniSeries.series == series_num
        ).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_genres(self, mini_series_code: int, genres: str) -> None:
        """Update genres for all episodes of a mini-series code."""
        stmt = update(MiniSeries).where(MiniSeries.code == mini_series_code).values(genres=genres)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_genres_by_code(self, mini_series_code: int) -> str | None:
        """Get genres for a mini-series code (from first available episode)."""
        stmt = select(MiniSeries.genres).where(MiniSeries.code == mini_series_code).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def move_to_feature_film(self, mini_series_code: int, series_num: int, new_code: int):
        """Moves a mini-series episode to FeatureFilm table with a new code."""
        # Get the episode
        stmt = select(MiniSeries).where(
            MiniSeries.code == mini_series_code,
            MiniSeries.series == series_num
        )
        result = await self.session.execute(stmt)
        episode = result.scalar_one_or_none()
        if not episode:
            raise ValueError("Episode not found")

        # Create new FeatureFilm
        from src.app.database.models import FeatureFilm
        new_film = FeatureFilm(
            code=new_code,
            name=episode.name,
            video_file_id=episode.video_file_id,
            captions=episode.captions
        )
        self.session.add(new_film)
        
        # Delete from MiniSeries
        await self.session.delete(episode)
        await self.session.commit()

    async def get_random_mini_series_first_episode(self) -> MiniSeries | None:
        """
        Get random mini-series, but only its first episode (series = 1).
        """
        try:
            stmt = (
                select(MiniSeries)
                .where(MiniSeries.series == 1)
                .order_by(func.random())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting random mini series: {e}")
            return None
    async def get_top_viewed_movies(self, limit: int = 20):
        stmt = (
            select(MiniSeries.code, func.sum(MiniSeries.views_count).label("count"))
            .group_by(MiniSeries.code)
            .order_by(func.sum(MiniSeries.views_count).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def increment_views(self, mini_series_code: int, series_num: int = 1):
        stmt = (
            update(MiniSeries)
            .where(MiniSeries.code == mini_series_code, MiniSeries.series == series_num)
            .values(views_count=MiniSeries.views_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.commit()
