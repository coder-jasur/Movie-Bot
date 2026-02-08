from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.app.database.models import Series

logger = logging.getLogger(__name__)


class SeriesActions:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_series(
            self,
            series_code: int,
            series_name: str,
            series_num: int,
            season: int,
            video_file_id: str,
            caption: str,
            genres: str = None,
    ):
        s = Series(
            code=series_code,
            name=series_name,
            season=season,
            series=series_num,
            video_file_id=video_file_id,
            captions=caption,
            genres=genres
        )
        # Update genres for all other episodes of the same series
        if genres:
            stmt = update(Series).where(Series.code == series_code).values(genres=genres)
            await self.session.execute(stmt)
            
        self.session.add(s)
        await self.session.commit()

    async def get_series(self, series_code: int) -> list[Series]:
        try:
            stmt = select(Series).where(Series.code == series_code).order_by(Series.season, Series.series)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting series {series_code}: {e}")
            return []

    async def delete_series(self, series_code: int):
        stmt = delete(Series).where(Series.code == series_code)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_season(self, series_code: int, season: int):
        stmt = delete(Series).where(Series.code == series_code, Series.season == season)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_series_for_season(self, series_code: int, series_num: int, season: int):
        stmt = delete(Series).where(
            Series.code == series_code,
            Series.series == series_num,
            Series.season == season
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_all_series(self) -> list[Series]:
        try:
            stmt = select(Series)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all series: {e}")
            return []

    async def update_series(self, series_code: int, **values):
        """Update metadata (Name/Caption) for ALL seasons/episodes of a series code."""
        stmt = update(Series).where(Series.code == series_code).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_episode_file(self, series_code: int, season: int, series_num: int, file_id: str):
        """Update file_id for a specific episode."""
        stmt = update(Series).where(
            Series.code == series_code,
            Series.season == season,
            Series.series == series_num
        ).values(video_file_id=file_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_movie_code(self, old_code: int, new_code: int) -> None:
        """
        Update the series code for all episodes.
        """
        # Check if new code exists
        existing = await self.get_series(new_code)
        if existing:
            raise ValueError(f"Code {new_code} already exists")

        stmt = (
            update(Series)
            .where(Series.code == old_code)
            .values(code=new_code)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_episode_details(self, series_code: int, old_season: int, old_series: int, **values):
        """
        Update specific episode details (season, series number).
        """
        stmt = update(Series).where(
            Series.code == series_code,
            Series.season == old_season,
            Series.series == old_series
        ).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_global_season(self, series_code: int, new_season: int):
        """Update season number for ALL episodes of a series code."""
        stmt = update(Series).where(Series.code == series_code).values(season=new_season)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_global_season_selective(self, series_code: int, old_season: int, new_season: int):
        """Update season number for specific season episodes of a series code."""
        stmt = update(Series).where(Series.code == series_code, Series.season == old_season).values(season=new_season)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_episode_metadata(self, series_code: int, season: int, series_num: int, **values):
        """Update name/caption for a specific episode."""
        stmt = update(Series).where(
            Series.code == series_code,
            Series.season == season,
            Series.series == series_num
        ).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_genres(self, series_code: int, genres: str) -> None:
        """Update genres for all episodes of a series code."""
        stmt = update(Series).where(Series.code == series_code).values(genres=genres)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_genres_by_code(self, series_code: int) -> str | None:
        """Get genres for a series code (from first available episode)."""
        stmt = select(Series.genres).where(Series.code == series_code).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def move_to_feature_film(self, series_code: int, season: int, series_num: int, new_code: int):
        """Moves an episode to FeatureFilm table with a new code."""
        # Get the episode
        stmt = select(Series).where(
            Series.code == series_code,
            Series.season == season,
            Series.series == series_num
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
        
        # Delete from Series
        await self.session.delete(episode)
        await self.session.commit()

    async def get_random_series_first_episode(self) -> Series | None:
        """
        Get random series, but only season=1 and series=1 (first episode of first season).
        """
        try:
            stmt = (
                select(Series)
                .where(Series.season == 1, Series.series == 1)
                .order_by(func.random())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting random series: {e}")
            return None
    async def get_top_viewed_movies(self, limit: int = 20):
        # For series, we group by code and sum views_count, or just take the max if it's per series? 
        # Actually it's better to sum if views are per episode, but let's assume views are mostly tracked on the main code entry.
        # But wait, Series model has code as part of primary key.
        stmt = (
            select(Series.code, func.sum(Series.views_count).label("count"))
            .group_by(Series.code)
            .order_by(func.sum(Series.views_count).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def increment_views(self, series_code: int, season: int = 1, series_num: int = 1):
        stmt = (
            update(Series)
            .where(Series.code == series_code, Series.season == season, Series.series == series_num)
            .values(views_count=Series.views_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.commit()
