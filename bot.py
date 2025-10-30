#!/usr/bin/env python3
"""
Car Assistant Bot - Telegram бот для владельцев автомобилей
"""

import asyncio
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from database.db import db
from handlers import admin, user
from utils.logger import setup_logging, get_logger

# Настройка логирования
logger = setup_logging()

# Загрузка переменных окружения
load_dotenv()

# Получение токена бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is required")
    sys.exit(1)

async def main():
    """Основная функция запуска бота"""
    try:
        # Подключение к базе данных
        await db.connect()
        logger.info("Database connected successfully")
        
        # Создание таблиц если их нет
        await create_tables()
        
        # Инициализация шаблонов
        await init_templates()
        
        # Инициализация администраторов
        await init_admins()
        
        # Создание бота и диспетчера
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
        dp = Dispatcher()
        
        # Регистрация роутеров
        dp.include_router(admin.router)
        dp.include_router(user.router)
        
        # Запуск бота
        logger.info("Starting bot...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Закрытие соединения с базой данных
        await db.close()
        logger.info("Bot stopped")

async def create_tables():
    """Создание таблиц в базе данных"""
    try:
        # Читаем SQL файл с схемой
        sql_file = Path(__file__).parent / "database" / "models.sql"
        if sql_file.exists():
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            async with db.pool.acquire() as conn:
                await conn.execute(sql_content)
            logger.info("Database tables created successfully")
        else:
            logger.warning("SQL schema file not found, tables may not be created")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

async def init_templates():
    """Инициализация шаблонов текстов в базе данных"""
    try:
        # Список шаблонов по умолчанию
        templates = [
            ('welcome_text', 'Привет! Я твой помощник по китайским машинам — помогу с эксплуатацией, ТО, ошибками и советами.', 'Приветственное сообщение при старте бота'),
            ('support_text', 'Поддержка готова помочь с вашим вопросом, пишите https://t.me/PerovV12', 'Текст для кнопки Написать в поддержку'),
            ('processing_text', '🤔 Обрабатываю ваш вопрос...', 'Сообщение при обработке вопроса пользователя'),
            ('rag_error_text', '⚠️ Не удалось получить ответ, попробуйте позже.', 'Сообщение об ошибке RAG API'),
            ('limit_exceeded_text', 'Превышен лимит вопросов', 'Сообщение о превышении лимита'),
            ('media_not_supported_text', 'Напишите свой вопрос. Картинки и аудио я пока не понимаю, но уже учусь)', 'Сообщение при получении картинок, аудио или других медиафайлов'),
        ]
        
        async with db.pool.acquire() as conn:
            for key, value, description in templates:
                await conn.execute("""
                    INSERT INTO text_templates (key, value, description)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """, key, value, description)
                logger.info(f"Template '{key}' initialized")
        
        logger.info("All templates initialized successfully")
        
    except Exception as e:
        logger.warning(f"Error initializing templates (may already exist): {e}")
        # Не падаем при ошибке, так как шаблоны могут уже существовать

async def init_admins():
    """Инициализация администраторов из переменной окружения"""
    try:
        admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
        if not admin_ids_str:
            logger.info("No ADMIN_USER_IDS set, skipping admin initialization")
            return
        
        # Парсим список админов
        admin_list = []
        for admin_str in admin_ids_str.split(','):
            admin_str = admin_str.strip()
            # Формат может быть: "363046871" или "363046871@ergottli
            parts = admin_str.split('@')
            if len(parts) > 0:
                user_id = parts[0].strip()
                try:
                    user_id_int = int(user_id)
                    # Формируем username: если есть @ в строке, берем часть после @, иначе создаем admin_{user_id}
                    if len(parts) > 1 and parts[1].strip():
                        username = f"@{parts[1].strip()}"
                    else:
                        username = f"admin_{user_id}"
                    admin_list.append((user_id_int, username))
                except ValueError:
                    logger.warning(f"Invalid admin ID: {admin_str}")
                    continue
        
        if not admin_list:
            logger.info("No valid admins found in ADMIN_USER_IDS")
            return
        
        # Добавляем админов в базу
        async with db.pool.acquire() as conn:
            for user_id, username in admin_list:
                await conn.execute("""
                    INSERT INTO users (user_id, username, role, allowed)
                    VALUES ($1, $2, 'admin', TRUE)
                    ON CONFLICT (user_id) DO UPDATE SET 
                        role = 'admin',
                        allowed = TRUE,
                        username = EXCLUDED.username
                """, user_id, username)
                logger.info(f"Admin {user_id} ({username}) initialized")
        
        logger.info(f"All {len(admin_list)} admin(s) initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing admins: {e}")
        raise

async def shutdown():
    """Корректное завершение работы бота"""
    logger.info("Shutting down bot...")
    await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
