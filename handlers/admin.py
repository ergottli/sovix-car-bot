from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

from database.db import db
from utils.helpers import parse_command_args, extract_user_id, format_users_list
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

async def get_user_id_by_username(bot: Bot, username: str) -> int | None:
    """
    Получение user_id по username через Telegram Bot API
    
    Args:
        bot: Экземпляр бота
        username: Username без @
        
    Returns:
        user_id или None если не найден
    """
    try:
        # Убираем @ если есть
        username = username.lstrip('@')
        
        # Используем getChat для получения информации о пользователе
        # Это работает только если пользователь уже взаимодействовал с ботом
        chat = await bot.get_chat(f"@{username}")
        return chat.id
    except Exception as e:
        logger.error(f"Error getting user_id for @{username}: {e}")
        return None

@router.message(Command("bootstrap"))
async def cmd_bootstrap(message: Message):
    """Команда создания первого администратора"""
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /bootstrap <секрет>")
        return
    
    secret = args[0]
    user_id = message.from_user.id
    username = message.from_user.username
    
    try:
        success = await db.bootstrap_admin(user_id, username, secret)
        if success:
            await message.reply("""✅ **Вы успешно зарегистрированы как администратор!**

Теперь вам доступны все административные команды:
• /add_user - Добавить пользователя
• /del_user - Удалить пользователя  
• /list_users - Список пользователей
• /pending_users - Пользователи в ожидании

Используйте /help для полной справки по командам.""")
        else:
            await message.reply("❌ Неверный секрет для регистрации администратора.")
    except Exception as e:
        logger.error(f"Error in bootstrap: {e}")
        await message.reply("❌ Произошла ошибка при регистрации администратора.")

@router.message(Command("add_user"))
async def cmd_add_user(message: Message):
    """Команда добавления пользователя (только для админов)"""
    # Проверяем права администратора
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /add_user <id или @username>")
        return
    
    user_identifier = args[0]
    
    try:
        user_id = None
        username = None
        
        # Если это @username, добавляем по username
        if user_identifier.startswith('@'):
            username = user_identifier.lstrip('@')
            
            # Сначала пытаемся получить user_id через API
            user_id = await get_user_id_by_username(message.bot, username)
            
            if user_id:
                # Пользователь уже взаимодействовал с ботом
                success = await db.add_user(user_id, username)
                if success:
                    await message.reply(f"✅ Пользователь @{username} (ID: {user_id}) успешно добавлен.")
                else:
                    await message.reply(f"❌ Не удалось добавить пользователя @{username}.")
            else:
                # Пользователь еще не взаимодействовал с ботом - добавляем с временным ID
                success = await db.add_user_by_username(username)
                if success:
                    await message.reply(f"✅ Пользователь @{username} добавлен в ожидании. Он получит доступ, когда впервые напишет боту.")
                else:
                    await message.reply(f"❌ Не удалось добавить пользователя @{username}.")
        else:
            # Извлекаем user_id из числового значения
            user_id = extract_user_id(user_identifier)
            if not user_id or not isinstance(user_id, int):
                await message.reply("❌ Неверный формат user_id. Используйте числовой ID или @username.")
                return
            username = f"user_{user_id}"
            
            # Добавляем пользователя
            success = await db.add_user(user_id, username)
            if success:
                await message.reply(f"✅ Пользователь {user_id} успешно добавлен.")
            else:
                await message.reply(f"❌ Не удалось добавить пользователя {user_id}.")
            
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        await message.reply("❌ Произошла ошибка при добавлении пользователя.")

@router.message(Command("del_user"))
async def cmd_delete_user(message: Message):
    """Команда удаления пользователя (только для админов)"""
    # Проверяем права администратора
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /del_user <id или @username>")
        return
    
    try:
        user_identifier = args[0]
        user_id = None
        
        # Если это @username, получаем user_id
        if user_identifier.startswith('@'):
            username = user_identifier.lstrip('@')
            user_id = await get_user_id_by_username(message.bot, username)
            
            if not user_id:
                await message.reply(f"❌ Не удалось найти пользователя @{username}. Убедитесь, что пользователь уже взаимодействовал с ботом.")
                return
        else:
            # Извлекаем user_id из числового значения
            user_id = extract_user_id(user_identifier)
            if not user_id or not isinstance(user_id, int):
                await message.reply("❌ Неверный формат user_id. Используйте числовой ID или @username.")
                return
        
        # Проверяем, что не удаляем себя
        if user_id == message.from_user.id:
            await message.reply("❌ Нельзя удалить самого себя.")
            return
        
        success = await db.delete_user(user_id)
        if success:
            if user_identifier.startswith('@'):
                await message.reply(f"✅ Пользователь @{user_identifier.lstrip('@')} (ID: {user_id}) успешно удален.")
            else:
                await message.reply(f"✅ Пользователь {user_id} успешно удален.")
        else:
            await message.reply(f"❌ Пользователь {user_id} не найден.")
            
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        await message.reply("❌ Произошла ошибка при удалении пользователя.")

@router.message(Command("list_users"))
async def cmd_list_users(message: Message):
    """Команда просмотра списка пользователей (только для админов)"""
    # Проверяем права администратора
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    # Парсим аргументы: [фильтр] [limit] [offset]
    filter_type = None
    limit = 50
    offset = 0
    
    if len(args) >= 1:
        filter_type = args[0]
    if len(args) >= 2:
        try:
            limit = int(args[1])
            limit = min(max(limit, 1), 100)  # Ограничиваем от 1 до 100
        except ValueError:
            await message.reply("❌ Неверный формат лимита. Используйте число от 1 до 100.")
            return
    if len(args) >= 3:
        try:
            offset = int(args[2])
            offset = max(offset, 0)  # Не может быть отрицательным
        except ValueError:
            await message.reply("❌ Неверный формат смещения. Используйте неотрицательное число.")
            return
    
    try:
        users = await db.list_users(filter_type, limit, offset)
        
        if not users:
            await message.reply("📋 Пользователи не найдены.")
            return
        
        # Форматируем список пользователей
        response = format_users_list(users, limit, offset)
        
        # Если сообщение слишком длинное, разбиваем на части
        if len(response) > 4000:
            # Разбиваем на части по 4000 символов
            parts = []
            current_part = ""
            for user in users:
                user_text = f"ID: {user['user_id']} | @{user['username']} | {user['role']} | {'✅' if user['allowed'] else '❌'}\n"
                if user['car'] != 'Не указан':
                    user_text += f"   🚗 {user['car']}\n"
                user_text += "\n"
                
                if len(current_part + user_text) > 4000:
                    parts.append(current_part.strip())
                    current_part = user_text
                else:
                    current_part += user_text
            
            if current_part.strip():
                parts.append(current_part.strip())
            
            for i, part in enumerate(parts):
                header = f"📋 Список пользователей (часть {i+1}/{len(parts)}):\n\n" if len(parts) > 1 else "📋 Список пользователей:\n\n"
                await message.reply(header + part)
        else:
            await message.reply(response)
            
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        await message.reply("❌ Произошла ошибка при получении списка пользователей.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    user_id = message.from_user.id
    is_admin = await db.is_admin(user_id)
    is_user_allowed = await db.is_user_allowed(user_id)
    
    if is_admin:
        # Справка для администраторов
        help_text = """🤖 **Car Assistant Bot - Справка для администратора**

**Основные команды:**
/set_car &lt;описание&gt; - Сохранить информацию об автомобиле
/my_car - Показать сохраненную информацию об автомобиле
/to - Получить контакт для записи на ТО
/help - Показать эту справку

**AI-помощник:**
Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!

**Команды администратора:**
/bootstrap &lt;секрет&gt; - Регистрация первого администратора
/add_user &lt;id или @username&gt; - Добавить пользователя
/del_user &lt;id или @username&gt; - Удалить пользователя
/list_users [фильтр] [лимит] [смещение] - Список пользователей
/pending_users - Пользователи в ожидании активации
/stat [период] - Статистика бота

**Фильтры для /list_users:**
- allowed - только разрешенные пользователи
- pending - только ожидающие разрешения
- admins - только администраторы
- users - только обычные пользователи
- name:&lt;текст&gt; - поиск по имени пользователя

**Периоды для /stat:**
- day - статистика за день
- month - статистика за месяц  
- year - статистика за год

**Примечание:** Пользователи, добавленные по @username, получат доступ при первом обращении к боту.

"""
    elif is_user_allowed:
        # Справка для обычных пользователей
        help_text = """🤖 **Car Assistant Bot - Справка для пользователя**

**Доступные команды:**
/set_car &lt;описание&gt; - Сохранить информацию об автомобиле
/my_car - Показать сохраненную информацию об автомобиле
/to - Получить контакт для записи на ТО
/help - Показать эту справку

**AI-помощник:**
Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!

**Примеры вопросов:**
- Как часто менять масло?
- Что делать, если загорелся индикатор Check Engine?
- Как подготовить автомобиль к зиме?
- Какие признаки неисправности тормозов?

"""
    else:
        # Справка для незалогиненных пользователей
        help_text = """🤖 **Car Assistant Bot - Добро пожаловать!**

**О боте:**
Я - ваш персональный помощник по вопросам автомобилей. Я могу помочь с техническими вопросами, диагностикой проблем и советами по обслуживанию.

**Для начала работы:**
Обратитесь к администратору для получения доступа к функциям бота.

**Что я умею:**
- Отвечать на вопросы об автомобилях
- Помогать с диагностикой проблем
- Давать советы по обслуживанию
- Сохранять информацию о вашем автомобиле
- Помогать с записью на ТО

**Команды (после получения доступа):**
/set_car &lt;описание&gt; - Сохранить информацию об автомобиле
/my_car - Показать информацию об автомобиле
/to - Получить контакт для записи на ТО
/help - Показать эту справку

"""
    
    await message.reply(help_text)

@router.message(Command("pending_users"))
async def cmd_pending_users(message: Message):
    """Команда просмотра пользователей в ожидании активации (только для админов)"""
    # Проверяем права администратора
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        pending_users = await db.get_pending_users()
        
        if not pending_users:
            await message.reply("📋 Пользователей в ожидании активации нет.")
            return
        
        response = "📋 **Пользователи в ожидании активации:**\n\n"
        
        for i, user in enumerate(pending_users, 1):
            username = user.get('username', 'N/A')
            created_at = user.get('created_at', 'N/A')
            response += f"{i}. @{username}\n"
            response += f"   Добавлен: {created_at}\n"
            response += f"   Статус: Ожидает первого обращения к боту\n\n"
        
        await message.reply(response)

    except Exception as e:
        logger.error(f"Error getting pending users: {e}")
        await message.reply("❌ Произошла ошибка при получении списка пользователей в ожидании.")

@router.message(Command("stat"))
async def cmd_stat(message: Message):
    """Команда получения статистики (только для админов)"""
    # Проверяем права администратора
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return

    command, args = parse_command_args(message.text)
    
    # Определяем период (по умолчанию - день)
    period = args[0] if args else "day"
    
    if period not in ["day", "month", "year"]:
        await message.reply("❌ Неверный период. Используйте: day, month или year")
        return

    try:
        stats = await db.get_statistics(period)
        
        # Форматируем период для отображения
        period_names = {
            "day": "день",
            "month": "месяц", 
            "year": "год"
        }
        period_display = period_names.get(period, period)
        
        response = f"""📊 **Статистика за {period_display}**

👥 **Пользователи:**
• Всего пользователей: {stats['total_users']}
• Активных за период: {stats['active_users']}
• Новых за период: {stats['new_users']}

💬 **Сообщения:**
• Всего сообщений: {stats['total_messages']}
• Команд: {stats['commands']}
• Текстовых сообщений: {stats['text_messages']}

🤖 **RAG API:**
• Запросов к AI: {stats['rag_requests']}

👑 **Топ пользователей по активности:**
"""
        
        if stats['top_users']:
            for i, user in enumerate(stats['top_users'], 1):
                username = user.get('username', 'N/A')
                message_count = user.get('message_count', 0)
                response += f"{i}. @{username}: {message_count} сообщений\n"
        else:
            response += "Нет данных\n"
        
        response += "\n📈 **Статистика по ролям:**\n"
        for role_stat in stats['role_stats']:
            role = role_stat.get('role', 'N/A')
            count = role_stat.get('count', 0)
            role_display = "Администраторы" if role == "admin" else "Пользователи"
            response += f"• {role_display}: {count}\n"
        
        await message.reply(response)

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        await message.reply("❌ Произошла ошибка при получении статистики.")
