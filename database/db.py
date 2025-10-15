import asyncpg
import os
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Подключение к базе данных"""
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.pool = await asyncpg.create_pool(database_url)
        logger.info("Connected to database")
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")
    
    async def bootstrap_admin(self, user_id: int, username: str, secret: str) -> bool:
        """Создание первого администратора"""
        admin_secret = os.getenv('ADMIN_BOOTSTRAP_SECRET')
        if secret != admin_secret:
            return False
        
        async with self.pool.acquire() as conn:
            # Обновляем существующего пользователя или создаем нового администратора
            await conn.execute("""
                INSERT INTO users (user_id, username, role, allowed)
                VALUES ($1, $2, 'admin', TRUE)
                ON CONFLICT (user_id) DO UPDATE SET 
                    role = 'admin',
                    allowed = TRUE,
                    username = EXCLUDED.username
            """, user_id, username)
            return True
    
    async def add_user(self, user_id: int, username: str) -> bool:
        """Добавление пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, role, allowed)
                VALUES ($1, $2, 'user', TRUE)
                ON CONFLICT (user_id) DO UPDATE SET allowed = TRUE
            """, user_id, username)
            return True
    
    async def add_user_by_username(self, username: str) -> bool:
        """Добавление пользователя по username (временный user_id = -1)"""
        async with self.pool.acquire() as conn:
            # Используем временный user_id = -1 для пользователей, добавленных по username
            await conn.execute("""
                INSERT INTO users (user_id, username, role, allowed)
                VALUES (-1, $1, 'user', TRUE)
                ON CONFLICT (user_id) DO NOTHING
            """, username)
            return True
    
    async def update_user_id_by_username(self, username: str, new_user_id: int) -> bool:
        """Обновление user_id для пользователя, добавленного по username"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE users 
                SET user_id = $1 
                WHERE username = $2 AND user_id = -1
            """, new_user_id, username)
            return result == "UPDATE 1"
    
    async def get_pending_users(self) -> List[Dict[str, Any]]:
        """Получение пользователей с временным user_id"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, username, role, allowed, car, created_at
                FROM users WHERE user_id = -1
                ORDER BY created_at ASC
            """)
            return [dict(row) for row in rows]
    
    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM users WHERE user_id = $1
            """, user_id)
            return result == "DELETE 1"
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT user_id, username, role, allowed, car, created_at
                FROM users WHERE user_id = $1
            """, user_id)
            return dict(row) if row else None
    
    async def is_user_allowed(self, user_id: int) -> bool:
        """Проверка разрешения доступа пользователя"""
        user = await self.get_user(user_id)
        return user and user['allowed']
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверка роли администратора"""
        user = await self.get_user(user_id)
        return user and user['role'] == 'admin'
    
    async def set_car(self, user_id: int, car_description: str) -> bool:
        """Сохранение информации об автомобиле"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET car = $1 WHERE user_id = $2
            """, car_description, user_id)
            return True
    
    async def get_car(self, user_id: int) -> Optional[str]:
        """Получение информации об автомобиле"""
        user = await self.get_user(user_id)
        return user['car'] if user else None
    
    async def list_users(self, filter_type: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Получение списка пользователей с фильтрацией"""
        async with self.pool.acquire() as conn:
            if filter_type == 'allowed':
                rows = await conn.fetch("""
                    SELECT user_id, username, role, allowed, car, created_at
                    FROM users WHERE allowed = TRUE
                    ORDER BY user_id ASC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            elif filter_type == 'pending':
                rows = await conn.fetch("""
                    SELECT user_id, username, role, allowed, car, created_at
                    FROM users WHERE allowed = FALSE
                    ORDER BY user_id ASC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            elif filter_type == 'admins':
                rows = await conn.fetch("""
                    SELECT user_id, username, role, allowed, car, created_at
                    FROM users WHERE role = 'admin'
                    ORDER BY user_id ASC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            elif filter_type == 'users':
                rows = await conn.fetch("""
                    SELECT user_id, username, role, allowed, car, created_at
                    FROM users WHERE role = 'user'
                    ORDER BY user_id ASC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            elif filter_type and filter_type.startswith('name:'):
                name_filter = filter_type[5:]  # Remove 'name:' prefix
                rows = await conn.fetch("""
                    SELECT user_id, username, role, allowed, car, created_at
                    FROM users WHERE username ILIKE $1
                    ORDER BY user_id ASC
                    LIMIT $2 OFFSET $3
                """, f'%{name_filter}%', limit, offset)
            else:
                rows = await conn.fetch("""
                    SELECT user_id, username, role, allowed, car, created_at
                    FROM users
                    ORDER BY user_id ASC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            
            return [dict(row) for row in rows]

# Глобальный экземпляр базы данных
db = Database()
