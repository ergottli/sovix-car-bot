import re
import base64
import urllib.parse
from typing import Optional, Tuple, List
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def parse_command_args(text: str) -> Tuple[str, List[str]]:
    """
    Парсинг аргументов команды
    
    Args:
        text: Текст команды
        
    Returns:
        Кортеж (команда, список аргументов)
    """
    parts = text.strip().split()
    if not parts:
        return "", []
    
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    return command, args

def extract_user_id(text: str) -> Optional[int]:
    """
    Извлечение user_id из текста (может быть числом или @username)
    
    Args:
        text: Текст с user_id или @username
        
    Returns:
        user_id или None если не найден
    """
    text = text.strip()
    
    # Если это число
    if text.isdigit():
        return int(text)
    
    # Если это @username, возвращаем как есть (будет обработан в handlers)
    if text.startswith('@'):
        return text
    
    return None

def validate_car_description(text: str) -> bool:
    """
    Валидация описания автомобиля
    
    Args:
        text: Описание автомобиля
        
    Returns:
        True если валидно, False иначе
    """
    if not text or len(text.strip()) < 3:
        return False
    
    # Проверяем на минимальную длину и отсутствие только спецсимволов
    clean_text = re.sub(r'[^\w\s\-.,]', '', text.strip())
    return len(clean_text) >= 3

def format_user_info(user: dict) -> str:
    """
    Форматирование информации о пользователе для вывода
    
    Args:
        user: Словарь с данными пользователя
        
    Returns:
        Отформатированная строка
    """
    user_id = user.get('user_id', 'N/A')
    username = user.get('username', 'N/A')
    role = user.get('role', 'N/A')
    allowed = "✅" if user.get('allowed') else "❌"
    car = user.get('car', 'Не указан')
    created_at = user.get('created_at', 'N/A')
    
    return f"""ID: {user_id}
Username: @{username}
Роль: {role}
Доступ: {allowed}
Автомобиль: {car}
Создан: {created_at}"""

def format_users_list(users: List[dict], limit: int = 50, offset: int = 0) -> str:
    """
    Форматирование списка пользователей
    
    Args:
        users: Список пользователей
        limit: Лимит записей
        offset: Смещение
        
    Returns:
        Отформатированный список
    """
    if not users:
        return "Пользователи не найдены."
    
    result = f"📋 Список пользователей (показано {len(users)} из {limit + offset}):\n\n"
    
    for i, user in enumerate(users, 1):
        user_id = user.get('user_id', 'N/A')
        username = user.get('username', 'N/A')
        role = user.get('role', 'N/A')
        allowed = "✅" if user.get('allowed') else "❌"
        car = user.get('car', 'Не указан')
        
        result += f"{i}. ID: {user_id} | @{username} | {role} | {allowed}\n"
        if car != 'Не указан':
            result += f"   🚗 {car}\n"
        result += "\n"
    
    return result.strip()

def sanitize_text(text: str) -> str:
    """
    Очистка текста от потенциально опасных символов
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    # Удаляем потенциально опасные символы, но оставляем обычные
    return re.sub(r'[<>"\']', '', text.strip())

def generate_deep_link(params: str, bot_username: str) -> str:
    """
    Генерация deep-link для Telegram бота
    
    Args:
        params: Параметры в формате "cmp=name&src=source&ad=banner"
        bot_username: Имя бота (без @)
        
    Returns:
        Полная ссылка вида https://t.me/BotUsername?start=payload
        
    Примеры:
        generate_deep_link("cmp=winter_2025&src=tg&ad=banner1", "car_sovix_bot")
        # Возвращает: https://t.me/car_sovix_bot?start=Y21wPXdpbnRlcl8yMDI1JnNyYz10ZyZhZD1iYW5uZXIx
    """
    # Кодируем в base64url (без = в конце и с безопасными символами для URL)
    payload = base64.urlsafe_b64encode(params.encode('utf-8')).decode('utf-8')
    
    # Убираем знаки = в конце, если есть (для URL-safe)
    payload = payload.rstrip('=')
    
    # Формируем финальную ссылку
    deep_link = f"https://t.me/{bot_username}?start={payload}"
    
    return deep_link

def parse_deep_link_params(params_str: str) -> dict:
    """
    Парсинг параметров deep-link
    
    Args:
        params_str: Строка параметров "cmp=name&src=source&ad=banner"
        
    Returns:
        Словарь с параметрами
    """
    params_dict = {}
    for pair in params_str.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            params_dict[key.strip()] = value.strip()
    return params_dict

def validate_deep_link_params(params_str: str) -> bool:
    """
    Валидация параметров deep-link
    
    Args:
        params_str: Строка параметров
        
    Returns:
        True если валидно
    """
    # Проверяем базовую структуру
    if not params_str or '=' not in params_str:
        return False
    
    # Проверяем наличие обязательных ключей
    required_keys = ['cmp', 'src', 'ad']
    keys = [p.split('=')[0] for p in params_str.split('&') if '=' in p]
    
    return all(key in keys for key in required_keys)
