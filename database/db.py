import asyncpg
import os
from typing import Optional, List, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

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
        # Нормализуем username - всегда храним с @
        if username and not username.startswith('@') and not username.startswith('user_'):
            username = f"@{username}"
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, role, allowed)
                VALUES ($1, $2, 'user', TRUE)
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
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
    
    async def log_rag_request(self, user_id: int, request_id: str, text: str, status: str = 'pending') -> None:
        """Логирование запроса к RAG API"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO rag_requests (user_id, request_id, text, status)
                VALUES ($1, $2, $3, $4)
            """, user_id, request_id, text, status)
    
    async def update_rag_request_status(self, request_id: str, status: str) -> None:
        """Обновление статуса запроса к RAG API"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE rag_requests SET status = $1 WHERE request_id = $2
            """, status, request_id)
    
    async def log_message(self, user_id: int, message_type: str, content: str) -> None:
        """Логирование сообщения"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO messages (user_id, message_type, content)
                VALUES ($1, $2, $3)
            """, user_id, message_type, content)
    
    async def get_statistics(self, period: str) -> Dict[str, Any]:
        """Получение статистики за период"""
        async with self.pool.acquire() as conn:
            # Определяем временной интервал
            if period == "day":
                time_filter = "created_at >= NOW() - INTERVAL '1 day'"
            elif period == "month":
                time_filter = "created_at >= NOW() - INTERVAL '1 month'"
            elif period == "year":
                time_filter = "created_at >= NOW() - INTERVAL '1 year'"
            else:
                time_filter = "created_at >= NOW() - INTERVAL '1 day'"
            
            # Общее количество пользователей
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            # Активные пользователи за период
            active_users = await conn.fetchval(f"""
                SELECT COUNT(DISTINCT user_id) 
                FROM messages 
                WHERE {time_filter}
            """)
            
            # Новые пользователи за период
            new_users = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM users 
                WHERE {time_filter}
            """)
            
            # Общее количество сообщений за период
            total_messages = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM messages 
                WHERE {time_filter}
            """)
            
            # Количество команд за период
            commands = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM messages 
                WHERE message_type = 'command' AND {time_filter}
            """)
            
            # Количество текстовых сообщений за период
            text_messages = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM messages 
                WHERE message_type = 'text' AND {time_filter}
            """)
            
            # Количество запросов к RAG API за период
            rag_requests = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM rag_requests 
                WHERE {time_filter}
            """)
            
            # Количество неудачных RAG запросов за период
            rag_failed = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM rag_requests 
                WHERE status = 'failed' AND {time_filter}
            """)
            
            # Количество установок машин за период
            car_setted = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM user_actions_log 
                WHERE action = 'set_car' AND {time_filter}
            """)
            
            # Количество достижений лимитов за период
            limits_exhausted = await conn.fetchval(f"""
                SELECT COUNT(*) 
                FROM user_actions_log 
                WHERE action = 'limit_exhausted' AND {time_filter}
            """)
            
            # Топ пользователей по активности
            top_users = await conn.fetch(f"""
                SELECT u.username, u.user_id, COUNT(m.id) as message_count
                FROM users u
                JOIN messages m ON u.user_id = m.user_id
                WHERE m.{time_filter}
                GROUP BY u.user_id, u.username
                ORDER BY message_count DESC
                LIMIT 5
            """)
            
            # Статистика по ролям
            role_stats = await conn.fetch(f"""
                SELECT role, COUNT(*) as count
                FROM users
                WHERE {time_filter}
                GROUP BY role
            """)
            
            return {
                "period": period,
                "total_users": total_users,
                "active_users": active_users,
                "new_users": new_users,
                "total_messages": total_messages,
                "commands": commands,
                "text_messages": text_messages,
                "rag_requests": rag_requests,
                "rag_failed": rag_failed,
                "car_setted": car_setted,
                "limits_exhausted": limits_exhausted,
                "top_users": [dict(row) for row in top_users],
                "role_stats": [dict(row) for row in role_stats]
            }
    
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
            # По умолчанию - последние добавленные (ORDER BY created_at DESC)
            rows = await conn.fetch("""
                SELECT user_id, username, role, allowed, car, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)
            
            return [dict(row) for row in rows]
    
    async def list_users_top(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение топ пользователей по количеству вопросов (rag_requests)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT u.user_id, u.username, u.role, u.allowed, u.car, u.created_at,
                       COUNT(r.id) as question_count
                FROM users u
                LEFT JOIN rag_requests r ON u.user_id = r.user_id
                GROUP BY u.user_id, u.username, u.role, u.allowed, u.car, u.created_at
                ORDER BY question_count DESC
                LIMIT $1
            """, limit)
            
            return [dict(row) for row in rows]
    
    async def list_all_users_for_csv(self) -> List[Dict[str, Any]]:
        """Получение всех пользователей для CSV экспорта"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT u.user_id, u.username, u.role, u.allowed, u.car, u.created_at,
                       COUNT(r.id) as question_count,
                       ua.src, ua.campaign, ua.ad
                FROM users u
                LEFT JOIN rag_requests r ON u.user_id = r.user_id
                LEFT JOIN user_acquisition ua ON u.user_id = ua.user_id
                GROUP BY u.user_id, u.username, u.role, u.allowed, u.car, u.created_at,
                         ua.src, ua.campaign, ua.ad
                ORDER BY u.created_at DESC
            """)
            
            return [dict(row) for row in rows]
    
    # Template management
    async def get_template(self, key: str) -> Optional[str]:
        """Получение шаблона текста по ключу"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM text_templates WHERE key = $1", key)
            return row['value'] if row else None
    
    async def set_template(self, key: str, value: str, description: str = None) -> bool:
        """Сохранение шаблона текста"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO text_templates (key, value, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, key, value, description)
            return True
    
    # Action logging
    async def log_action(self, user_id: int, action: str, object_data: str = None) -> None:
        """Логирование действия пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_actions_log (user_id, action, object)
                VALUES ($1, $2, $3)
            """, user_id, action, object_data)
    
    # User acquisition tracking
    async def save_user_acquisition(self, user_id: int, payload_raw: str, payload_decoded: str, 
                                   src: str, campaign: str, ad: str, language_code: str) -> bool:
        """Сохранение информации о привлечении пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_acquisition (user_id, payload_raw, payload_decoded, src, campaign, ad, language_code)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (user_id) DO NOTHING
            """, user_id, payload_raw, payload_decoded, src, campaign, ad, language_code)
            return True
    
    async def get_user_acquisition(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о привлечении пользователя"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT user_id, payload_raw, payload_decoded, src, campaign, ad, language_code
                FROM user_acquisition WHERE user_id = $1
            """, user_id)
            return dict(row) if row else None
    
    # User limits management
    async def get_user_limits(self, user_id: int) -> Dict[str, Any]:
        """Получение лимитов пользователя"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT absolute_limit, absolute_used, weekly_limit, weekly_used, week_start
                FROM user_limits WHERE user_id = $1
            """, user_id)
            
            if row:
                return dict(row)
            else:
                # Создаем запись с лимитами по умолчанию
                await conn.execute("""
                    INSERT INTO user_limits (user_id, absolute_limit, weekly_limit)
                    VALUES ($1, NULL, NULL)
                """, user_id)
                return {
                    'absolute_limit': None,
                    'absolute_used': 0,
                    'weekly_limit': None,
                    'weekly_used': 0,
                    'week_start': None
                }
    
    async def check_and_increment_limits(self, user_id: int):
        """
        Проверка и увеличение лимитов пользователя
        Returns: (can_proceed, error_message)
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT absolute_limit, absolute_used, weekly_limit, weekly_used, week_start
                FROM user_limits WHERE user_id = $1
            """, user_id)
            
            # Если запись не существует, создаем её
            if not row:
                await conn.execute("""
                    INSERT INTO user_limits (user_id)
                    VALUES ($1)
                """, user_id)
                row = await conn.fetchrow("""
                    SELECT absolute_limit, absolute_used, weekly_limit, weekly_used, week_start
                    FROM user_limits WHERE user_id = $1
                """, user_id)
            
            limits = dict(row)
            
            # Проверяем абсолютный лимит
            if limits['absolute_limit'] is not None:
                if limits['absolute_used'] >= limits['absolute_limit']:
                    return False, "absolute_limit_exceeded"
            
            # Проверяем недельный лимит
            if limits['weekly_limit'] is not None:
                from datetime import datetime, timedelta
                import pytz
                tz = pytz.UTC
                now = datetime.now(tz)
                
                # Если не было недели или прошла неделя, сбрасываем
                if limits['week_start'] is None:
                    week_start = now
                else:
                    week_start = limits['week_start'] if isinstance(limits['week_start'], datetime) else datetime.fromisoformat(str(limits['week_start']))
                    if not week_start.tzinfo:
                        week_start = tz.localize(week_start)
                
                week_duration = timedelta(days=7)
                if now - week_start >= week_duration:
                    # Сбрасываем недельный лимит
                    await conn.execute("""
                        UPDATE user_limits 
                        SET weekly_used = 0, week_start = NOW()
                        WHERE user_id = $1
                    """, user_id)
                    limits['weekly_used'] = 0
                    limits['week_start'] = now
                else:
                    if limits['weekly_used'] >= limits['weekly_limit']:
                        return False, "weekly_limit_exceeded"
            
            # Увеличиваем лимиты
            await conn.execute("""
                UPDATE user_limits
                SET absolute_used = absolute_used + 1,
                    weekly_used = weekly_used + 1,
                    week_start = COALESCE(week_start, NOW())
                WHERE user_id = $1
            """, user_id)
            
            return True, ""
    
    async def update_user_limits(self, user_id: int, absolute_limit: int = None, weekly_limit: int = None) -> bool:
        """Обновление лимитов пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE user_limits
                SET absolute_limit = $1, weekly_limit = $2
                WHERE user_id = $3
            """, absolute_limit, weekly_limit, user_id)
            return True
    
    async def update_all_users_limits(self, absolute_limit: int = None, weekly_limit: int = None) -> bool:
        """Обновление лимитов для всех пользователей"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE user_limits
                SET absolute_limit = $1, weekly_limit = $2
            """, absolute_limit, weekly_limit)
            return True
    
    async def get_user_analytics(self, user_id: int, period: str = "day") -> Dict[str, Any]:
        """Получение аналитики по пользователю"""
        async with self.pool.acquire() as conn:
            # Определяем временной интервал
            if period == "day":
                time_filter = "created_at >= NOW() - INTERVAL '1 day'"
            elif period == "month":
                time_filter = "created_at >= NOW() - INTERVAL '1 month'"
            elif period == "year":
                time_filter = "created_at >= NOW() - INTERVAL '1 year'"
            else:
                time_filter = "created_at >= NOW() - INTERVAL '1 day'"
            
            # Количество сообщений
            total_messages = await conn.fetchval(f"""
                SELECT COUNT(*) FROM messages
                WHERE user_id = $1 AND {time_filter}
            """, user_id)
            
            # Команды
            commands = await conn.fetchval(f"""
                SELECT COUNT(*) FROM messages
                WHERE user_id = $1 AND message_type = 'command' AND {time_filter}
            """, user_id)
            
            # Текстовые сообщения
            text_messages = await conn.fetchval(f"""
                SELECT COUNT(*) FROM messages
                WHERE user_id = $1 AND message_type = 'text' AND {time_filter}
            """, user_id)
            
            # RAG запросы
            rag_requests = await conn.fetchval(f"""
                SELECT COUNT(*) FROM rag_requests
                WHERE user_id = $1 AND {time_filter}
            """, user_id)
            
            # RAG ошибки
            rag_failed = await conn.fetchval(f"""
                SELECT COUNT(*) FROM rag_requests
                WHERE user_id = $1 AND status = 'failed' AND {time_filter}
            """, user_id)
            
            # Установка машины
            car_setted = await conn.fetchval(f"""
                SELECT COUNT(*) FROM user_actions_log
                WHERE user_id = $1 AND action = 'set_car' AND {time_filter}
            """, user_id)
            
            # Достижение лимитов
            limits_exhausted = await conn.fetchval(f"""
                SELECT COUNT(*) FROM user_actions_log
                WHERE user_id = $1 AND action = 'limit_exhausted' AND {time_filter}
            """, user_id)
            
            # Информация о пользователе
            user = await self.get_user(user_id)
            acquisition = await self.get_user_acquisition(user_id)
            limits = await self.get_user_limits(user_id)
            
            is_blocked = not user['allowed'] if user else True
            is_admin = user['role'] == 'admin' if user else False
            car_name = user['car'] if user and user.get('car') else None
            
            # Проверяем достижение лимитов
            limits_reached = False
            if limits['absolute_limit'] is not None and limits['absolute_used'] >= limits['absolute_limit']:
                limits_reached = True
            elif limits['weekly_limit'] is not None and limits['weekly_used'] >= limits['weekly_limit']:
                limits_reached = True
            
            return {
                'user_id': user_id,
                'username': user['username'] if user else None,
                'first_seen_at': user['created_at'] if user else None,
                'last_seen_at': None,
                'total_messages': total_messages,
                'command_messages': commands,
                'text_messages': text_messages,
                'rag_requests': rag_requests,
                'rag_failed': rag_failed,
                'is_blocked': is_blocked,
                'is_admin': is_admin,
                'car': car_name,
                'limits_reached': limits_reached,
                'src': acquisition['src'] if acquisition else None,
                'campaign': acquisition['campaign'] if acquisition else None,
                'ad': acquisition['ad'] if acquisition else None,
                'car_setted': car_setted,
                'limits_exhausted': limits_exhausted
            }

# Глобальный экземпляр базы данных
db = Database()
