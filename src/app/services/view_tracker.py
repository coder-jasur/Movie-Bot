from redis.asyncio import Redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ViewTracker:
    """View tracking xizmati - Redis connection pool bilan"""
    
    _redis_pool: Optional[Redis] = None
    
    @classmethod
    async def get_redis(cls, redis_url: str) -> Redis:
        """Redis connection pool - singleton pattern"""
        if cls._redis_pool is None:
            cls._redis_pool = Redis.from_url(
                redis_url,
                max_connections=50,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            logger.info("ViewTracker Redis pool created")
        return cls._redis_pool
    
    @classmethod
    async def close(cls):
        """Redis connection'ni yopish"""
        if cls._redis_pool:
            await cls._redis_pool.close()
            cls._redis_pool = None
    
    @classmethod
    async def is_new_view(cls, redis_url: str, user_id: int, movie_code: int) -> bool:
        """Foydalanuvchi bu filmni bugun ko'rganmi tekshirish
        
        Args:
            redis_url: Redis URL
            user_id: Foydalanuvchi ID
            movie_code: Film kodi
            
        Returns:
            True - yangi ko'rish, False - bugun allaqachon ko'rgan
        """
        try:
            redis = await cls.get_redis(redis_url)
            key = f"view:{user_id}:{movie_code}"
            is_set = await redis.set(key, "1", ex=86400, nx=True)
            return bool(is_set)
        except Exception as e:
            logger.error(f"ViewTracker error for user {user_id}, movie {movie_code}: {e}")
            return False  # Xatolik bo'lsa, view count oshmasin
    
    @classmethod
    async def increment_pending_view(cls, redis_url: str, movie_code: int, movie_type: str, season: int = None, series: int = None):
        """Pending view'ni Redis'da increment qilish (batch update uchun)
        
        Args:
            redis_url: Redis URL
            movie_code: Film kodi
            movie_type: 'feature' | 'series' | 'mini_series'
            season: Serial uchun season raqami
            series: Serial/mini-serial uchun series raqami
        """
        try:
            redis = await cls.get_redis(redis_url)
            
            if movie_type == "feature":
                key = f"views:pending:feature:{movie_code}"
            elif movie_type == "series":
                key = f"views:pending:series:{movie_code}:{season}:{series}"
            elif movie_type == "mini_series":
                key = f"views:pending:mini:{movie_code}:{series}"
            else:
                logger.error(f"Unknown movie type: {movie_type}")
                return
            
            await redis.hincrby("views:pending", key, 1)
        except Exception as e:
            logger.error(f"Increment pending view error: {e}")
    
    @classmethod
    async def get_pending_views(cls, redis_url: str) -> dict:
        """Barcha pending view'larni olish"""
        try:
            redis = await cls.get_redis(redis_url)
            pending = await redis.hgetall("views:pending")
            return pending if pending else {}
        except Exception as e:
            logger.error(f"Get pending views error: {e}")
            return {}
    
    @classmethod
    async def clear_pending_views(cls, redis_url: str):
        """Pending view'larni tozalash"""
        try:
            redis = await cls.get_redis(redis_url)
            await redis.delete("views:pending")
        except Exception as e:
            logger.error(f"Clear pending views error: {e}")
