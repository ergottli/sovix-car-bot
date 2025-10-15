from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import logging

from database.db import db
from utils.helpers import parse_command_args, extract_user_id, format_users_list

logger = logging.getLogger(__name__)
router = Router()

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
            await message.reply("✅ Вы успешно зарегистрированы как администратор!")
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
        # Если это @username, нужно получить user_id
        if user_identifier.startswith('@'):
            # В реальном приложении здесь нужно получить user_id по username
            # Для простоты будем считать, что это уже user_id
            await message.reply("❌ Добавление по @username пока не поддерживается. Используйте user_id.")
            return
        
        # Извлекаем user_id
        user_id = extract_user_id(user_identifier)
        if not user_id or not isinstance(user_id, int):
            await message.reply("❌ Неверный формат user_id. Используйте числовой ID.")
            return
        
        # Добавляем пользователя
        success = await db.add_user(user_id, f"user_{user_id}")
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
        await message.reply("❌ Использование: /del_user <id>")
        return
    
    try:
        user_id = extract_user_id(args[0])
        if not user_id or not isinstance(user_id, int):
            await message.reply("❌ Неверный формат user_id. Используйте числовой ID.")
            return
        
        # Проверяем, что не удаляем себя
        if user_id == message.from_user.id:
            await message.reply("❌ Нельзя удалить самого себя.")
            return
        
        success = await db.delete_user(user_id)
        if success:
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
    is_admin = await db.is_admin(message.from_user.id)
    
    help_text = """🤖 **Car Assistant Bot - Помощь**

**Основные команды:**
/set_car <описание> - Сохранить информацию об автомобиле
/my_car - Показать сохраненную информацию об автомобиле
/to - Получить контакт для записи на ТО
/help - Показать эту справку

**AI-помощник:**
Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!

"""
    
    if is_admin:
        help_text += """**Команды администратора:**
/bootstrap <секрет> - Регистрация первого администратора
/add_user <id> - Добавить пользователя
/del_user <id> - Удалить пользователя
/list_users [фильтр] [лимит] [смещение] - Список пользователей

**Фильтры для /list_users:**
- allowed - только разрешенные пользователи
- pending - только ожидающие разрешения
- admins - только администраторы
- users - только обычные пользователи
- name:<текст> - поиск по имени пользователя

"""
    
    await message.reply(help_text, parse_mode="Markdown")
