"""
Модуль для настройки логирования
"""
import logging
import os
import sys


def setup_logging():
    """Настройка системы логирования"""
    # Получаем настройки из переменных окружения
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Преобразуем строку уровня в константу logging
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    log_level_value = level_mapping.get(log_level, logging.INFO)
    
    # Настраиваем форматтер
    formatter = logging.Formatter(log_format)
    
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_value)
    
    # Очищаем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Только обработчик для консоли (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_value)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Настраиваем уровни для конкретных логгеров
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncpg').setLevel(logging.WARNING)
    
    # Логируем информацию о настройке
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, Output: stdout only")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Получение логгера с указанным именем"""
    return logging.getLogger(name)
