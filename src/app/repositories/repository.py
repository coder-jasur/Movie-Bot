import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.models import FeatureFilm, Series, MiniSeries

logger = logging.getLogger(__name__)


class SearchRepository:
    """Film qidirish - PostgreSQL ILIKE bilan optimallashtirilgan"""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_feature_films(self, query: str, limit: int = 20) -> list[tuple]:
        """Feature filmlarni qidirish
        
        Args:
            query: Qidiruv so'zi
            limit: Maksimal natijalar soni
            
        Returns:
            List of (film, score) tuples
        """
        try:
            # PostgreSQL ILIKE - case-insensitive search
            stmt = (
                select(FeatureFilm)
                .where(FeatureFilm.name.ilike(f"%{query}%"))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            films = result.scalars().all()
            
            # Score hisoblash - qanchalik aniq mos kelsa, shuncha yuqori
            results = []
            for film in films:
                # Oddiy scoring - to'liq mos kelsa 100, qisman mos kelsa kamroq
                name_lower = film.name.lower()
                query_lower = query.lower()
                
                if name_lower == query_lower:
                    score = 100
                elif name_lower.startswith(query_lower):
                    score = 95
                elif query_lower in name_lower:
                    score = 90
                else:
                    score = 85
                
                results.append((film, score))
            
            # Score bo'yicha tartiblash
            results.sort(key=lambda x: x[1], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching feature films: {e}")
            return []

    async def search_series(self, query: str, limit: int = 20) -> list[tuple]:
        """Seriallarni qidirish - faqat unique code'lar"""
        try:
            # Unique code'lar uchun DISTINCT
            stmt = (
                select(Series)
                .where(Series.name.ilike(f"%{query}%"))
                .distinct(Series.code)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            series_list = result.scalars().all()
            
            # Unique by code
            unique_series = {}
            for s in series_list:
                if s.code not in unique_series:
                    unique_series[s.code] = s
            
            # Score hisoblash
            results = []
            for series in unique_series.values():
                name_lower = series.name.lower()
                query_lower = query.lower()
                
                if name_lower == query_lower:
                    score = 100
                elif name_lower.startswith(query_lower):
                    score = 95
                elif query_lower in name_lower:
                    score = 90
                else:
                    score = 85
                
                results.append((series, score))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching series: {e}")
            return []

    async def search_mini_series(self, query: str, limit: int = 20) -> list[tuple]:
        """Mini-seriallarni qidirish - faqat unique code'lar"""
        try:
            stmt = (
                select(MiniSeries)
                .where(MiniSeries.name.ilike(f"%{query}%"))
                .distinct(MiniSeries.code)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            mini_list = result.scalars().all()
            
            # Unique by code
            unique_mini = {}
            for m in mini_list:
                if m.code not in unique_mini:
                    unique_mini[m.code] = m
            
            # Score hisoblash
            results = []
            for mini in unique_mini.values():
                name_lower = mini.name.lower()
                query_lower = query.lower()
                
                if name_lower == query_lower:
                    score = 100
                elif name_lower.startswith(query_lower):
                    score = 95
                elif query_lower in name_lower:
                    score = 90
                else:
                    score = 85
                
                results.append((mini, score))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching mini series: {e}")
            return []

