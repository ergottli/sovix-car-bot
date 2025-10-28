from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
import os
import csv
import io
from datetime import datetime

from database.db import db
from utils.helpers import parse_command_args, extract_user_id, format_users_list, validate_deep_link_params, parse_deep_link_params, generate_deep_link
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

def get_root_admins() -> list:
    """Получение списка корневых админов из переменной окружения"""
    admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
    if not admin_ids_str:
        return []
    
    try:
        return [int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip().isdigit()]
    except:
        return []

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
        await message.reply("❌ Использование: /bootstrap <секрет>", parse_mode=None)
        return
    
    secret = args[0]
    user_id = message.from_user.id
    username = message.from_user.username
    
    try:
        success = await db.bootstrap_admin(user_id, username, secret)
        if success:
            await message.reply("""✅ <b>Вы успешно зарегистрированы как администратор!</b>

Теперь вам доступны все административные команды:
• /add_user - Добавить пользователя
• /del_user - Удалить пользователя  
• /list_users - Список пользователей
• /pending_users - Пользователи в ожидании

Используйте /help для полной справки по командам.""", parse_mode="HTML")
        else:
            await message.reply("❌ Неверный секрет для регистрации администратора.")
    except Exception as e:
        logger.error(f"Error in bootstrap: {e}")
        await message.reply("❌ Произошла ошибка при регистрации администратора.")

@router.message(Command("del_user"))
async def cmd_delete_user(message: Message):
    """Команда удаления пользователя (только для админов)"""
    # Проверяем права администратора
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /del_user <id или @username>", parse_mode=None)
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
    """Команда просмотра списка пользователей (только для админов)
    
    /list_users - последние 50 пользователей
    /list_users top - топ 50 по количеству вопросов
    /list_users csv - выгрузка CSV
    """
    # Проверяем права администратора
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    mode = args[0] if args else "default"
    
    try:
        if mode == "csv":
            # CSV выгрузка
            users = await db.list_all_users_for_csv()
            
            if not users:
                await message.reply("📋 Пользователи не найдены.")
                return
            
            # Формируем CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовок
            writer.writerow([
                'user_id', 'username', 'role', 'allowed', 'car', 'created_at',
                'question_count', 'src', 'campaign', 'ad'
            ])
            
            # Данные
            for user in users:
                writer.writerow([
                    user['user_id'],
                    user['username'],
                    user['role'],
                    user['allowed'],
                    user.get('car', ''),
                    user['created_at'],
                    user.get('question_count', 0),
                    user.get('src', ''),
                    user.get('campaign', ''),
                    user.get('ad', '')
                ])
            
            csv_content = output.getvalue()
            csv_bytes = csv_content.encode('utf-8')
            
            from aiogram.types import BufferedInputFile
            await message.reply_document(
                BufferedInputFile(csv_bytes, filename="users.csv"),
                caption="📊 Список всех пользователей"
            )
            
        elif mode == "top":
            # Топ 50 по количеству вопросов
            users = await db.list_users_top(50)
            
            if not users:
                await message.reply("📋 Пользователи не найдены.")
                return
            
            response = "📋 <b>Топ пользователей по количеству вопросов:</b>\n\n"
            
            for i, user in enumerate(users, 1):
                username = user.get('username', 'N/A')
                user_id = user['user_id']
                question_count = user.get('question_count', 0)
                allowed = "✅" if user['allowed'] else "❌"
                
                response += f"{i}. @{username} (ID: {user_id}) {allowed}\n"
                response += f"   📝 Вопросов: {question_count}\n\n"
                
                if len(response) > 3500:  # Оставляем место для заголовка
                    await message.reply(response, parse_mode="HTML")
                    response = ""
            
            if response:
                await message.reply(response, parse_mode="HTML")
                
        else:
            # По умолчанию - последние 50 пользователей
            users = await db.list_users(limit=50, offset=0)
            
            if not users:
                await message.reply("📋 Пользователи не найдены.")
                return
            
            response = "📋 <b>Последние пользователи:</b>\n\n"
            
            for i, user in enumerate(users, 1):
                username = user.get('username', 'N/A')
                user_id = user['user_id']
                role = user['role']
                allowed = "✅" if user['allowed'] else "❌"
                car = user.get('car', '')
                
                response += f"{i}. @{username} (ID: {user_id})\n"
                response += f"   Роль: {role} {allowed}\n"
                if car:
                    response += f"   🚗 {car}\n"
                response += "\n"
                
                if len(response) > 3500:
                    await message.reply(response, parse_mode="HTML")
                    response = ""
            
            if response:
                await message.reply(response, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        await message.reply("❌ Произошла ошибка при получении списка пользователей.")

@router.message(Command("generate_link"))
async def cmd_generate_link(message: Message):
    """Команда генерации deep-link для отслеживания источников трафика"""
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        help_text = """🔗 <b>Генерация рекламных ссылок</b>

<b>Использование:</b>
/generate_link параметры

<b>Формат параметров:</b>
cmp=название_кампании&src=источник&ad=баннер

<b>Примеры:</b>
/generate_link cmp=winter_2025_blogger&src=tg&ad=banner1
/generate_link cmp=summer2025&src=fb&ad=post1
/generate_link cmp=test&src=vk&ad=banner2

<b>Параметры:</b>
• <code>cmp</code> - название кампании (например: winter_2025_blogger)
• <code>src</code> - источник (например: tg, fb, vk, youtube)
• <code>ad</code> - ID баннера/поста (например: banner1)

<b>Результат:</b>
Бот вернёт готовую ссылку для размещения в рекламе."""
        await message.reply(help_text, parse_mode="HTML")
        return
    
    # Объединяем все аргументы в одну строку
    params_str = " ".join(args)
    
    # Валидация параметров
    if not validate_deep_link_params(params_str):
        await message.reply(
            "❌ Неверный формат параметров.\n\n"
            "Используйте: cmp=name&src=source&ad=banner\n"
            "Пример: /generate_link cmp=winter_2025&src=tg&ad=banner1",
            parse_mode=None
        )
        return
    
    try:
        # Получаем имя бота из переменных окружения
        import os
        bot_username = os.getenv('BOT_USERNAME', 'car_sovix_bot')
        
        # Генерируем ссылку
        deep_link = generate_deep_link(params_str, bot_username)
        
        # Парсим параметры для отображения
        params = parse_deep_link_params(params_str)
        
        # Формируем ответ
        response = f"""🔗 <b>Рекламная ссылка</b>

<b>Параметры:</b>
• Кампания: <code>{params.get('cmp', 'N/A')}</code>
• Источник: <code>{params.get('src', 'N/A')}</code>
• Баннер: <code>{params.get('ad', 'N/A')}</code>

<b>Готовая ссылка:</b>
<code>{deep_link}</code>

<b>Использование:</b>
Разместите эту ссылку в вашем рекламном объявлении. 
Пользователи, перешедшие по ней, будут автоматически отслежены в статистике."""
        
        await message.reply(response, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error generating deep link: {e}")
        await message.reply("❌ Произошла ошибка при генерации ссылки.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    user_id = message.from_user.id
    is_admin = await db.is_admin(user_id)
    is_user_allowed = await db.is_user_allowed(user_id)
    
    if is_admin:
        # Справка для администраторов
        help_text = """🤖 <b>Car Assistant Bot - Справка для администратора</b>

<b>Основные команды:</b>
/my_car - Посмотреть/изменить свой автомобиль
/set_car - Указать автомобиль
/support - Написать в поддержку
/help - Показать эту справку

<b>AI-помощник:</b>
Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!

<b>Команды администратора:</b>
/add_admin @username - Добавить администратора
/del_admin @username - Удалить права администратора
/block_user tg_id/@username - Заблокировать пользователя
/unblock_user tg_id/@username - Разблокировать пользователя
/list_users - Последние 50 пользователей
/list_users top - Топ 50 по количеству вопросов
/list_users csv - Выгрузка всех пользователей в CSV
/change_user_week_limit N - Изменить недельный лимит для всех
/change_user_week_limit tg_id/@username N - Лимит для пользователя
/change_user_abs_limit N - Изменить абсолютный лимит для всех
/change_user_abs_limit tg_id/@username N - Лимит для пользователя

<b>🔗 Рекламные ссылки:</b>
/generate_link cmp=кампания&src=источник&ad=баннер

<b>📊 Аналитика и статистика:</b>
/stat [период] - Базовая статистика
/stat users [период] csv - Суммаризация (CSV)
/stat users_per_day [период] csv - По пользователям (CSV)

<b>Примеры:</b>
/generate_link cmp=winter_2025&src=tg&ad=banner1
/stat day - статистика за день
/stat users month csv - суммаризация за месяц
/stat users_per_day day csv - по пользователям за день

<b>Периоды:</b> day (по умолчанию), month (30 дней), year (365 дней)

<b>Примечание:</b> Пользователи, добавленные по @username, получат доступ при первом обращении к боту.

"""
    elif is_user_allowed:
        # Справка для обычных пользователей
        help_text = """🤖 <b>Car Assistant Bot - Справка для пользователя</b>

<b>Доступные команды:</b>
/my_car - Посмотреть/изменить свой автомобиль
/set_car - Указать автомобиль
/support - Написать в поддержку
/help - Показать эту справку

<b>Меню бота:</b>
• Моя машина 🚘
• Написать в поддержку

<b>AI-помощник:</b>
Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!

<b>Примеры вопросов:</b>
- Как часто менять масло?
- Что делать, если загорелся индикатор Check Engine?
- Как подготовить автомобиль к зиме?
- Какие признаки неисправности тормозов?

"""
    else:
        # Справка для незалогиненных пользователей
        help_text = """🤖 <b>Car Assistant Bot - Добро пожаловать!</b>

<b>О боте:</b>
Я - ваш персональный помощник по вопросам китайских автомобилей. Я могу помочь с эксплуатацией, техническим обслуживанием, диагностикой ошибок и советами.

<b>Что я умею:</b>
- Отвечать на вопросы об автомобилях
- Помогать с диагностикой проблем
- Давать советы по обслуживанию
- Сохранять информацию о вашем автомобиле

<b>Доступные команды:</b>
/my_car - Посмотреть/изменить свой автомобиль
/set_car - Указать автомобиль
/support - Написать в поддержку
/help - Показать эту справку

Просто напишите любой вопрос, и я постараюсь помочь!

"""
    
    await message.reply(help_text, parse_mode="HTML")

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
        
        response = "📋 <b>Пользователи в ожидании активации:</b>\n\n"
        
        for i, user in enumerate(pending_users, 1):
            username = user.get('username', 'N/A')
            created_at = user.get('created_at', 'N/A')
            response += f"{i}. @{username}\n"
            response += f"   Добавлен: {created_at}\n"
            response += f"   Статус: Ожидает первого обращения к боту\n\n"
        
        await message.reply(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error getting pending users: {e}")
        await message.reply("❌ Произошла ошибка при получении списка пользователей в ожидании.")

@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message):
    """Команда добавления администратора (только для корневых админов)"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь корневым админом
    root_admins = get_root_admins()
    if user_id not in root_admins:
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /add_admin @username", parse_mode=None)
        return
    
    # Нормализуем username - убираем все @ и добавляем один
    username = args[0].lstrip('@')
    normalized_username = f"@{username}"
    
    try:
        async with db.pool.acquire() as conn:
            # Проверяем, есть ли пользователь с таким username в базе
            existing_user = await conn.fetchrow("""
                SELECT user_id, role FROM users WHERE username = $1
            """, normalized_username)
            
            if existing_user:
                # Пользователь уже есть - обновляем роль
                await conn.execute("""
                    UPDATE users
                    SET role = 'admin', allowed = TRUE
                    WHERE user_id = $1
                """, existing_user['user_id'])
                
                if existing_user['user_id'] < 0:
                    await message.reply(f"✅ Пользователь {normalized_username} добавлен как администратор. Получит права при первом обращении к боту.")
                else:
                    await message.reply(f"✅ Пользователь {normalized_username} (ID: {existing_user['user_id']}) теперь администратор.")
            else:
                # Пользователя нет - создаем с уникальным временным ID (отрицательный хеш от username)
                # Используем простой хеш для генерации уникального отрицательного ID
                temp_id = -abs(hash(username)) % (10 ** 10)
                
                await conn.execute("""
                    INSERT INTO users (user_id, username, role, allowed)
                    VALUES ($1, $2, 'admin', TRUE)
                    ON CONFLICT (user_id) DO NOTHING
                """, temp_id, normalized_username)
                
                await message.reply(f"✅ Пользователь {normalized_username} добавлен как администратор. Получит права при первом обращении к боту.")
        
    except Exception as e:
        logger.error(f"Error adding admin: {e}")
        await message.reply("❌ Произошла ошибка при добавлении администратора.")

@router.message(Command("del_admin"))
async def cmd_del_admin(message: Message):
    """Команда удаления администратора (только для корневых админов)"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь корневым админом
    root_admins = get_root_admins()
    if user_id not in root_admins:
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /del_admin @username", parse_mode=None)
        return
    
    # Нормализуем username - убираем все @ и добавляем один
    username = args[0].lstrip('@')
    normalized_username = f"@{username}"
    
    try:
        async with db.pool.acquire() as conn:
            # Ищем пользователя по username (может быть с временным ID)
            target_user = await conn.fetchrow("""
                SELECT user_id, role FROM users WHERE username = $1
            """, normalized_username)
            
            if not target_user:
                await message.reply(f"❌ Пользователь {normalized_username} не найден в базе.")
                return
            
            target_user_id = target_user['user_id']
            
            # Проверяем, не пытается ли админ удалить самого себя
            if target_user_id == user_id:
                await message.reply("❌ Нельзя удалить права администратора у самого себя.")
                return
            
            # Проверяем, не является ли удаляемый пользователь корневым админом
            if target_user_id in root_admins or target_user_id < 0:
                # Для пользователей с временным ID или корневых админов
                if target_user_id in root_admins:
                    await message.reply("❌ Нельзя удалить права у корневого администратора.")
                    return
            
            # Понижаем администратора до обычного пользователя
            await conn.execute("""
                UPDATE users
                SET role = 'user'
                WHERE user_id = $1
            """, target_user_id)
            
            if target_user_id < 0:
                await message.reply(f"✅ Права администратора удалены у {normalized_username} (активируется при первом обращении).")
            else:
                await message.reply(f"✅ Пользователь {normalized_username} (ID: {target_user_id}) больше не администратор.")
        
    except Exception as e:
        logger.error(f"Error removing admin: {e}")
        await message.reply("❌ Произошла ошибка при удалении администратора.")

@router.message(Command("block_user"))
async def cmd_block_user(message: Message):
    """Команда блокировки пользователя"""
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /block_user tg_id/@username", parse_mode=None)
        return
    
    try:
        user_identifier = args[0]
        
        async with db.pool.acquire() as conn:
            # Если это @username, ищем в базе
            if user_identifier.startswith('@'):
                username = user_identifier.lstrip('@')
                normalized_username = f"@{username}"
                target_user = await conn.fetchrow("""
                    SELECT user_id FROM users WHERE username = $1
                """, normalized_username)
                
                if not target_user:
                    await message.reply(f"❌ Пользователь {normalized_username} не найден в базе.")
                    return
                
                user_id = target_user['user_id']
            else:
                # Извлекаем user_id из числового значения
                user_id = extract_user_id(user_identifier)
                if not user_id or not isinstance(user_id, int):
                    await message.reply("❌ Неверный формат user_id. Используйте числовой ID или @username.", parse_mode=None)
                    return
            
            # Блокируем пользователя
            result = await conn.execute("""
                UPDATE users SET allowed = FALSE WHERE user_id = $1
            """, user_id)
            
            if result == "UPDATE 0":
                await message.reply(f"❌ Пользователь с ID {user_id} не найден в базе.")
            else:
                if user_identifier.startswith('@'):
                    await message.reply(f"✅ Пользователь {normalized_username} (ID: {user_id}) заблокирован.")
                else:
                    await message.reply(f"✅ Пользователь {user_id} заблокирован.")
        
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        await message.reply("❌ Произошла ошибка при блокировке пользователя.")

@router.message(Command("unblock_user"))
async def cmd_unblock_user(message: Message):
    """Команда разблокировки пользователя"""
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /unblock_user tg_id/@username", parse_mode=None)
        return
    
    try:
        user_identifier = args[0]
        
        async with db.pool.acquire() as conn:
            # Если это @username, ищем в базе
            if user_identifier.startswith('@'):
                username = user_identifier.lstrip('@')
                normalized_username = f"@{username}"
                target_user = await conn.fetchrow("""
                    SELECT user_id FROM users WHERE username = $1
                """, normalized_username)
                
                if not target_user:
                    await message.reply(f"❌ Пользователь {normalized_username} не найден в базе.")
                    return
                
                user_id = target_user['user_id']
            else:
                # Извлекаем user_id из числового значения
                user_id = extract_user_id(user_identifier)
                if not user_id or not isinstance(user_id, int):
                    await message.reply("❌ Неверный формат user_id. Используйте числовой ID или @username.", parse_mode=None)
                    return
            
            # Разблокируем пользователя
            result = await conn.execute("""
                UPDATE users SET allowed = TRUE WHERE user_id = $1
            """, user_id)
            
            if result == "UPDATE 0":
                await message.reply(f"❌ Пользователь с ID {user_id} не найден в базе.")
            else:
                if user_identifier.startswith('@'):
                    await message.reply(f"✅ Пользователь {normalized_username} (ID: {user_id}) разблокирован.")
                else:
                    await message.reply(f"✅ Пользователь {user_id} разблокирован.")
        
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        await message.reply("❌ Произошла ошибка при разблокировке пользователя.")

@router.message(Command("change_user_week_limit"))
async def cmd_change_user_week_limit(message: Message):
    """Команда изменения недельного лимита пользователя"""
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if len(args) < 1:
        await message.reply("❌ Использование: /change_user_week_limit N или /change_user_week_limit tg_id/@username N")
        return
    
    try:
        # Проверяем, указан ли пользователь
        if len(args) == 1:
            # Изменяем для всех
            limit_value = args[0]
            if limit_value.lower() == 'off':
                limit_value = None
            else:
                limit_value = int(limit_value)
                if limit_value <= 0:
                    await message.reply("❌ Лимит должен быть больше 0.")
                    return
            
            await db.update_all_users_limits(weekly_limit=limit_value)
            await message.reply(f"✅ Недельный лимит для всех пользователей изменен на {limit_value if limit_value else 'off'}.")
        else:
            # Изменяем для конкретного пользователя
            user_identifier = args[0]
            limit_value = args[1]
            
            # Получаем user_id
            async with db.pool.acquire() as conn:
                if user_identifier.startswith('@'):
                    username = user_identifier.lstrip('@')
                    normalized_username = f"@{username}"
                    target_user = await conn.fetchrow("""
                        SELECT user_id FROM users WHERE username = $1
                    """, normalized_username)
                    
                    if not target_user:
                        await message.reply(f"❌ Пользователь {normalized_username} не найден в базе.")
                        return
                    
                    user_id = target_user['user_id']
                else:
                    user_id = extract_user_id(user_identifier)
                    if not user_id or not isinstance(user_id, int):
                        await message.reply("❌ Неверный формат user_id. Используйте числовой ID или @username.", parse_mode=None)
                        return
            
            # Парсим лимит
            if limit_value.lower() == 'off':
                limit_value = None
            else:
                limit_value = int(limit_value)
                if limit_value <= 0:
                    await message.reply("❌ Лимит должен быть больше 0.")
                    return
            
            await db.update_user_limits(user_id=user_id, weekly_limit=limit_value)
            
            if user_identifier.startswith('@'):
                await message.reply(f"✅ Недельный лимит для пользователя {normalized_username} изменен на {limit_value if limit_value else 'off'}.")
            else:
                await message.reply(f"✅ Недельный лимит для пользователя {user_id} изменен на {limit_value if limit_value else 'off'}.")
        
    except ValueError:
        await message.reply("❌ Неверный формат лимита.")
    except Exception as e:
        logger.error(f"Error changing week limit: {e}")
        await message.reply("❌ Произошла ошибка при изменении лимита.")

@router.message(Command("change_user_abs_limit"))
async def cmd_change_user_abs_limit(message: Message):
    """Команда изменения абсолютного лимита пользователя"""
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    if len(args) < 1:
        await message.reply("❌ Использование: /change_user_abs_limit N или /change_user_abs_limit tg_id/@username N")
        return
    
    try:
        # Проверяем, указан ли пользователь
        if len(args) == 1:
            # Изменяем для всех
            limit_value = args[0]
            if limit_value.lower() == 'off':
                limit_value = None
            else:
                limit_value = int(limit_value)
                if limit_value <= 0:
                    await message.reply("❌ Лимит должен быть больше 0.")
                    return
            
            await db.update_all_users_limits(absolute_limit=limit_value)
            await message.reply(f"✅ Абсолютный лимит для всех пользователей изменен на {limit_value if limit_value else 'off'}.")
        else:
            # Изменяем для конкретного пользователя
            user_identifier = args[0]
            limit_value = args[1]
            
            # Получаем user_id
            async with db.pool.acquire() as conn:
                if user_identifier.startswith('@'):
                    username = user_identifier.lstrip('@')
                    normalized_username = f"@{username}"
                    target_user = await conn.fetchrow("""
                        SELECT user_id FROM users WHERE username = $1
                    """, normalized_username)
                    
                    if not target_user:
                        await message.reply(f"❌ Пользователь {normalized_username} не найден в базе.")
                        return
                    
                    user_id = target_user['user_id']
                else:
                    user_id = extract_user_id(user_identifier)
                    if not user_id or not isinstance(user_id, int):
                        await message.reply("❌ Неверный формат user_id. Используйте числовой ID или @username.", parse_mode=None)
                        return
            
            # Парсим лимит
            if limit_value.lower() == 'off':
                limit_value = None
            else:
                limit_value = int(limit_value)
                if limit_value <= 0:
                    await message.reply("❌ Лимит должен быть больше 0.")
                    return
            
            await db.update_user_limits(user_id=user_id, absolute_limit=limit_value)
            
            if user_identifier.startswith('@'):
                await message.reply(f"✅ Абсолютный лимит для пользователя {normalized_username} изменен на {limit_value if limit_value else 'off'}.")
            else:
                await message.reply(f"✅ Абсолютный лимит для пользователя {user_id} изменен на {limit_value if limit_value else 'off'}.")
        
    except ValueError:
        await message.reply("❌ Неверный формат лимита.")
    except Exception as e:
        logger.error(f"Error changing absolute limit: {e}")
        await message.reply("❌ Произошла ошибка при изменении лимита.")

@router.message(Command("stat"))
async def cmd_stat_export(message: Message):
    """Команда статистики и экспорта в CSV"""
    if not await db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return
    
    command, args = parse_command_args(message.text)
    
    # Проверяем, какая подкоманда
    if not args or args[0] not in ["users", "users_per_day"]:
        # Базовая статистика (старый обработчик /stat)
        period = args[0] if args and args[0] in ["day", "month", "year"] else "day"
        
        try:
            stats = await db.get_statistics(period)
            
            # Форматируем период для отображения
            period_names = {
                "day": "день",
                "month": "месяц", 
                "year": "год"
            }
            period_display = period_names.get(period, period)
            
            response = f"""📊 <b>Статистика за {period_display}</b>

👥 <b>Пользователи:</b>
• Всего пользователей: {stats['total_users']}
• Активных за период: {stats['active_users']}
• Новых за период: {stats['new_users']}

💬 <b>Сообщения:</b>
• Всего сообщений: {stats['total_messages']}
• Команд: {stats['commands']}
• Текстовых сообщений: {stats['text_messages']}

🤖 <b>RAG API:</b>
• Запросов к AI: {stats['rag_requests']}
• Неудачных запросов: {stats['rag_failed']}

📈 <b>Действия:</b>
• Установок машин: {stats['car_setted']}
• Достижений лимитов: {stats['limits_exhausted']}

👑 <b>Топ пользователей по активности:</b>
"""
            
            if stats['top_users']:
                for i, user in enumerate(stats['top_users'], 1):
                    username = user.get('username', 'N/A')
                    message_count = user.get('message_count', 0)
                    response += f"{i}. {username}: {message_count} сообщений\n"
            else:
                response += "Нет данных\n"
            
            response += "\n📈 <b>Статистика по ролям:</b>\n"
            for role_stat in stats['role_stats']:
                role = role_stat.get('role', 'N/A')
                count = role_stat.get('count', 0)
                role_display = "Администраторы" if role == "admin" else "Пользователи"
                response += f"• {role_display}: {count}\n"
            
            await message.reply(response, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            await message.reply("❌ Произошла ошибка при получении статистики.")
        return
    
    # CSV экспорт
    subcommand = args[0]
    
    # Определяем период (по умолчанию - день)
    period = args[1] if len(args) > 1 and args[1] in ["day", "month", "year"] else "day"
    
    # Проверяем, нужен ли CSV экспорт
    needs_csv = "csv" in [a.lower() for a in args]
    
    if not needs_csv:
        await message.reply("❌ Для экспорта добавьте параметр 'csv'.\nПример: /stat users day csv")
        return
    
    try:
        # Вычисляем period_start и period_end
        from datetime import datetime, timedelta
        import pytz
        
        now = datetime.now(pytz.UTC)
        if period == "day":
            period_start = now - timedelta(days=1)
        elif period == "month":
            period_start = now - timedelta(days=30)
        elif period == "year":
            period_start = now - timedelta(days=365)
        else:
            period_start = now - timedelta(days=1)
        
        period_end = now
        period_start_str = period_start.strftime('%Y-%m-%d %H:%M:%S')
        period_end_str = period_end.strftime('%Y-%m-%d %H:%M:%S')
        
        if subcommand == "users":
            # Суммаризированная статистика
            stats = await db.get_statistics(period)
            
            # Формируем CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовок
            writer.writerow([
                'period_start', 'period_end', 'total_users', 'active_users', 'new_users',
                'total_messages', 'command_messages', 'text_messages', 'rag_requests',
                'rag_failed', 'car_setted', 'limits_exhausted'
            ])
            
            # Данные
            writer.writerow([
                period_start_str, period_end_str, stats['total_users'], stats['active_users'], stats['new_users'],
                stats['total_messages'], stats['commands'], stats['text_messages'], stats['rag_requests'],
                stats['rag_failed'], stats['car_setted'], stats['limits_exhausted']
            ])
            
            csv_content = output.getvalue()
            
        elif subcommand == "users_per_day":
            # Статистика по пользователям
            users = await db.list_users()
            
            # Формируем CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовок
            writer.writerow([
                'period_start', 'period_end', 'user_id', 'username', 'first_seen_at', 'last_seen_at', 
                'total_messages', 'command_messages', 'text_messages', 'rag_requests', 'rag_failed',
                'is_blocked', 'is_admin', 'car', 'limits_reached', 'src', 'campaign', 'ad',
                'car_setted', 'limits_exhausted'
            ])
            
            # Данные для каждого пользователя
            for user_id in [u['user_id'] for u in users]:
                analytics = await db.get_user_analytics(user_id, period)
                writer.writerow([
                    period_start_str, period_end_str,
                    analytics['user_id'], analytics['username'], analytics['first_seen_at'],
                    analytics['last_seen_at'], analytics['total_messages'], analytics['command_messages'],
                    analytics['text_messages'], analytics['rag_requests'], analytics['rag_failed'],
                    analytics['is_blocked'], analytics['is_admin'], analytics['car'],
                    analytics['limits_reached'], analytics['src'], analytics['campaign'], analytics['ad'],
                    analytics['car_setted'], analytics['limits_exhausted']
                ])
            
            csv_content = output.getvalue()
        
        # Отправляем файл
        csv_bytes = csv_content.encode('utf-8')
        from aiogram.types import BufferedInputFile
        await message.reply_document(
            BufferedInputFile(csv_bytes, filename=f"stat_{period}.csv"),
            caption=f"📊 Статистика за {period}"
        )
        
    except Exception as e:
        logger.error(f"Error exporting statistics: {e}")
        await message.reply("❌ Произошла ошибка при экспорте статистики.")
