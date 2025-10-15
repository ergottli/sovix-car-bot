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
