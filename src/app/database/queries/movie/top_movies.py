from datetime import datetime, timedelta
from sqlalchemy import select, func, literal, union_all, or_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.app.database.models import FeatureFilm, Series, MiniSeries, Favorite

logger = logging.getLogger(__name__)


class TopMoviesActions:
    """Top filmlar uchun optimallashtirilgan query'lar"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_top_movies(self, interval: str = "total", limit: int = 20) -> list[dict]:
        # ... (rest of existing method)
        """Top filmlarni olish - database darajasida agregatsiya
        
        Args:
            interval: 'day' | 'week' | 'month' | 'total'
            limit: Nechta film qaytarish
            
        Returns:
            List of dicts with movie info and stats
        """
        try:
            # Interval uchun filter
            start_date = self._get_start_date(interval)
            
            # Feature Films query
            feature_query = (
                select(
                    FeatureFilm.code.label("code"),
                    FeatureFilm.name.label("name"),
                    literal("Film").label("type"),
                    func.coalesce(func.count(func.distinct(Favorite.user_id)), 0).label("favs"),
                    FeatureFilm.views_count.label("views"),
                    (func.coalesce(func.count(func.distinct(Favorite.user_id)), 0) * 10 + FeatureFilm.views_count).label("score")
                )
                .outerjoin(Favorite, FeatureFilm.code == Favorite.movie_code)
            )
            
            if start_date:
                feature_query = feature_query.where(Favorite.created_at >= start_date)
            
            feature_query = feature_query.group_by(FeatureFilm.code, FeatureFilm.name, FeatureFilm.views_count)
            
            # Series query - group by code
            series_query = (
                select(
                    Series.code.label("code"),
                    func.max(Series.name).label("name"),
                    literal("Serial").label("type"),
                    func.coalesce(func.count(func.distinct(Favorite.user_id)), 0).label("favs"),
                    func.sum(Series.views_count).label("views"),
                    (func.coalesce(func.count(func.distinct(Favorite.user_id)), 0) * 10 + func.sum(Series.views_count)).label("score")
                )
                .outerjoin(Favorite, Series.code == Favorite.movie_code)
            )
            
            if start_date:
                series_query = series_query.where(Favorite.created_at >= start_date)
            
            series_query = series_query.group_by(Series.code)
            
            # MiniSeries query - group by code
            mini_query = (
                select(
                    MiniSeries.code.label("code"),
                    func.max(MiniSeries.name).label("name"),
                    literal("Epizodli film").label("type"),
                    func.coalesce(func.count(func.distinct(Favorite.user_id)), 0).label("favs"),
                    func.sum(MiniSeries.views_count).label("views"),
                    (func.coalesce(func.count(func.distinct(Favorite.user_id)), 0) * 10 + func.sum(MiniSeries.views_count)).label("score")
                )
                .outerjoin(Favorite, MiniSeries.code == Favorite.movie_code)
            )
            
            if start_date:
                mini_query = mini_query.where(Favorite.created_at >= start_date)
            
            mini_query = mini_query.group_by(MiniSeries.code)
            
            # UNION ALL - barcha turlarni birlashtirish
            combined_query = union_all(feature_query, series_query, mini_query).subquery()
            
            # Final query - sorting va limit
            final_query = (
                select(combined_query)
                .order_by(combined_query.c.score.desc())
                .limit(limit)
            )
            
            result = await self.session.execute(final_query)
            rows = result.all()
            
            # Dict'ga konvertatsiya
            movies = []
            for row in rows:
                movies.append({
                    "code": row.code,
                    "name": row.name,
                    "type": row.type,
                    "favs": row.favs,
                    "views": row.views,
                    "score": row.score
                })
            
            return movies
            
        except Exception as e:
            logger.error(f"Error getting top movies: {e}")
            return []
    
    async def get_top_by_genres(self, genres: list[str], limit: int = 10) -> list[dict]:
        """Janrlar bo'yicha top filmlarni olish
        
        Args:
            genres: Tanlangan janrlar ro'yxati
            limit: Natijalar soni
            
        Returns:
            List of dicts with movie info
        """
        try:
            if not genres:
                return []
            
            # LIKE operatori uchun filterlarni tayyorlash
            # JSON array ichidan qidirish: %"JanrName"%
            genre_filters = [f'%"{g}"%' for g in genres]
            
            # Feature Films query
            feature_query = (
                select(
                    FeatureFilm.code.label("code"),
                    FeatureFilm.name.label("name"),
                    literal("Film").label("type"),
                    FeatureFilm.genres.label("genres"),
                    func.coalesce(func.count(func.distinct(Favorite.user_id)), 0).label("favs"),
                    FeatureFilm.views_count.label("views"),
                    (func.coalesce(func.count(func.distinct(Favorite.user_id)), 0) * 10 + FeatureFilm.views_count).label("score")
                )
                .outerjoin(Favorite, FeatureFilm.code == Favorite.movie_code)
                .where(or_(*[FeatureFilm.genres.like(f) for f in genre_filters]))
                .group_by(FeatureFilm.code, FeatureFilm.name, FeatureFilm.views_count, FeatureFilm.genres)
            )
            
            # Series query
            series_query = (
                select(
                    Series.code.label("code"),
                    func.max(Series.name).label("name"),
                    literal("Serial").label("type"),
                    Series.genres.label("genres"),
                    func.coalesce(func.count(func.distinct(Favorite.user_id)), 0).label("favs"),
                    func.sum(Series.views_count).label("views"),
                    (func.coalesce(func.count(func.distinct(Favorite.user_id)), 0) * 10 + func.sum(Series.views_count)).label("score")
                )
                .outerjoin(Favorite, Series.code == Favorite.movie_code)
                .where(or_(*[Series.genres.like(f) for f in genre_filters]))
                .group_by(Series.code, Series.genres)
            )
            
            # MiniSeries query
            mini_query = (
                select(
                    MiniSeries.code.label("code"),
                    func.max(MiniSeries.name).label("name"),
                    literal("Epizodli film").label("type"),
                    MiniSeries.genres.label("genres"),
                    func.coalesce(func.count(func.distinct(Favorite.user_id)), 0).label("favs"),
                    func.sum(MiniSeries.views_count).label("views"),
                    (func.coalesce(func.count(func.distinct(Favorite.user_id)), 0) * 10 + func.sum(MiniSeries.views_count)).label("score")
                )
                .outerjoin(Favorite, MiniSeries.code == Favorite.movie_code)
                .where(or_(*[MiniSeries.genres.like(f) for f in genre_filters]))
                .group_by(MiniSeries.code, MiniSeries.genres)
            )
            
            combined_query = union_all(feature_query, series_query, mini_query).subquery()
            
            final_query = (
                select(combined_query)
                .order_by(combined_query.c.score.desc())
                .limit(limit)
            )
            
            result = await self.session.execute(final_query)
            rows = result.all()
            
            movies = []
            for row in rows:
                movies.append({
                    "code": row.code,
                    "name": row.name,
                    "type": row.type,
                    "favs": row.favs,
                    "views": row.views,
                    "score": row.score,
                    "genres": row.genres
                })
            
            return movies
            
        except Exception as e:
            logger.error(f"Error getting top by genres: {e}")
            return []

    def _get_start_date(self, interval: str) -> datetime | None:
        """Interval uchun start date hisoblash"""
        if interval == "total":
            return None
        
        now = datetime.now()
        
        if interval == "day":
            return now - timedelta(days=1)
        elif interval == "week":
            return now - timedelta(days=7)
        elif interval == "month":
            return now - timedelta(days=30)
        elif interval == "year":
            return now - timedelta(days=365)
        
        return None
