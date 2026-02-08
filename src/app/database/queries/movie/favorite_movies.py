from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.models import Favorite


class FavoriteMoviesActions:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_favorite_movie(
            self,
            movie_code: int,
            user_id: int
    ):
        stmt = insert(Favorite).values(user_id=user_id, movie_code=movie_code)
        stmt = stmt.on_conflict_do_nothing(index_elements=['user_id', 'movie_code'])
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_favorites(
            self,
            movie_code: int,
            user_id: int
    ):
        stmt = select(Favorite).where(Favorite.user_id == user_id, Favorite.movie_code == movie_code)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all_favorites_by_user_id(self, user_id: int):
        stmt = select(Favorite).where(Favorite.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all_favorites(self):
        stmt = select(Favorite)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_top_favorite_movies(self, interval: str = "total", limit: int = 20):
        from datetime import datetime, timedelta
        
        stmt = (
            select(
                Favorite.movie_code,
                func.count(Favorite.movie_code).label("count")
            )
            .group_by(Favorite.movie_code)
            .order_by(func.count(Favorite.movie_code).desc())
            .limit(limit)
        )

        if interval != "total":
            now = datetime.now()
            if interval == "day":
                start_date = now - timedelta(days=1)
            elif interval == "week":
                start_date = now - timedelta(days=7)
            elif interval == "month":
                start_date = now - timedelta(days=30)
            elif interval == "year":
                start_date = now - timedelta(days=365)
            else:
                start_date = None
            
            if start_date:
                stmt = stmt.where(Favorite.created_at >= start_date)

        result = await self.session.execute(stmt)
        return result.all()

    async def delete_favorite_movie(self, movie_code: int, user_id: int):
        stmt = delete(Favorite).where(Favorite.user_id == user_id, Favorite.movie_code == movie_code)
        await self.session.execute(stmt)
        await self.session.commit()
