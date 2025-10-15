from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database.db import db
from utils.helpers import parse_command_args, validate_car_description, sanitize_text
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

@router.message(Command("set_car"))
async def cmd_set_car(message: Message):
    """Команда сохранения информации об автомобиле"""
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"User {user_id} (@{username}) executed /set_car command")
    
    # Проверяем права доступа
    if not await db.is_user_allowed(user_id):
        logger.warning(f"User {user_id} (@{username}) tried to use /set_car without permission")
        await message.reply("❌ У вас нет доступа к функциям бота. Обратитесь к администратору.")
        return
    
    command, args = parse_command_args(message.text)
    
    if not args:
        await message.reply("❌ Использование: /set_car <описание автомобиля>")
        return
    
    car_description = " ".join(args)
    
    # Валидируем описание
    if not validate_car_description(car_description):
        await message.reply("❌ Описание автомобиля слишком короткое. Минимум 3 символа.")
        return
    
    # Очищаем текст
    car_description = sanitize_text(car_description)
    
    try:
        success = await db.set_car(message.from_user.id, car_description)
        
        # Логируем команду
        await db.log_message(message.from_user.id, "command", f"set_car: {car_description[:100]}...")
        
        if success:
            await message.reply(f"✅ Информация об автомобиле сохранена:\n🚗 {car_description}")
        else:
            await message.reply("❌ Не удалось сохранить информацию об автомобиле.")
    except Exception as e:
        logger.error(f"Error setting car: {e}")
        await message.reply("❌ Произошла ошибка при сохранении информации об автомобиле.")

@router.message(Command("my_car"))
async def cmd_my_car(message: Message):
    """Команда просмотра сохраненной информации об автомобиле"""
    # Проверяем права доступа
    if not await db.is_user_allowed(message.from_user.id):
        await message.reply("❌ У вас нет доступа к функциям бота. Обратитесь к администратору.")
        return
    
    try:
        # Логируем команду
        await db.log_message(message.from_user.id, "command", "my_car")
        
        car_info = await db.get_car(message.from_user.id)
        if car_info:
            await message.reply(f"🚗 **Ваш автомобиль:**\n{car_info}", parse_mode="Markdown")
        else:
            await message.reply("❌ Информация об автомобиле не сохранена.\nИспользуйте /set_car <описание> для сохранения.")
    except Exception as e:
        logger.error(f"Error getting car: {e}")
        await message.reply("❌ Произошла ошибка при получении информации об автомобиле.")

@router.message(Command("to"))
async def cmd_to(message: Message):
    """Команда получения контакта для записи на ТО"""
    # Проверяем права доступа
    if not await db.is_user_allowed(message.from_user.id):
        await message.reply("❌ У вас нет доступа к функциям бота. Обратитесь к администратору.")
        return
    
    # В первой версии просто возвращаем контактный телефон
    try:
        # Логируем команду
        await db.log_message(message.from_user.id, "command", "to")
        
        contact_info = """🔧 **Запись на ТО**

Для записи на техническое обслуживание обращайтесь:

📞 **Телефон:** +7 (XXX) XXX-XX-XX
🕒 **Время работы:** Пн-Пт: 9:00-18:00, Сб: 9:00-15:00
📍 **Адрес:** [Адрес сервисного центра]

Или оставьте заявку через бота, и мы свяжемся с вами."""
        
        await message.reply(contact_info, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in to command: {e}")
        await message.reply("❌ Произошла ошибка при получении контакта.")

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда старта бота"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    try:
        # Проверяем, есть ли пользователь в базе
        user = await db.get_user(user_id)
        
        # Если пользователя нет, но есть username, проверяем, не добавлен ли он по username
        if not user and username:
            # Пытаемся обновить user_id для пользователя, добавленного по username
            success = await db.update_user_id_by_username(username, user_id)
            if success:
                # Перезагружаем данные пользователя
                user = await db.get_user(user_id)
        
        if not user:
            await message.reply("""👋 **Добро пожаловать в Car Assistant Bot!**

Я помогу вам с вопросами о вашем автомобиле.

❌ **У вас пока нет доступа к функциям бота.**
Обратитесь к администратору для получения доступа.

После получения доступа вы сможете:
• Сохранить информацию о своем автомобиле
• Задавать вопросы о техническом обслуживании
• Записываться на ТО
• Получать советы по уходу за автомобилем

Используйте /help для получения подробной справки.""")
        else:
            if user['allowed']:
                # Проверяем, является ли пользователь администратором
                is_admin = await db.is_admin(user_id)
                
                if is_admin:
                    await message.reply("""👋 **Добро пожаловать в Car Assistant Bot!**

✅ **Вы вошли как администратор.**

**Основные команды:**
/set_car &lt;описание&gt; - Сохранить информацию об автомобиле
/my_car - Показать информацию об автомобиле
/to - Записаться на ТО
/help - Справка по командам

**Команды администратора:**
/add_user &lt;id или @username&gt; - Добавить пользователя
/del_user &lt;id или @username&gt; - Удалить пользователя
/list_users - Список пользователей
/pending_users - Пользователи в ожидании

Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!""")
                else:
                    await message.reply("""👋 **Добро пожаловать в Car Assistant Bot!**

✅ **У вас есть доступ к функциям бота.**

**Доступные команды:**
/set_car &lt;описание&gt; - Сохранить информацию об автомобиле
/my_car - Показать информацию об автомобиле
/to - Записаться на ТО
/help - Справка по командам

**AI-помощник:**
Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!

**Примеры вопросов:**
- Как часто менять масло?
- Что делать, если загорелся индикатор Check Engine?
- Как подготовить автомобиль к зиме?""")
            else:
                await message.reply("""👋 **Добро пожаловать в Car Assistant Bot!**

❌ **У вас пока нет доступа к функциям бота.**
Обратитесь к администратору для получения доступа.

Используйте /help для получения подробной справки.""")
                
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка текстовых сообщений (вопросы к AI)"""
    user_id = message.from_user.id
    username = message.from_user.username
    question = message.text[:100] + "..." if len(message.text) > 100 else message.text
    logger.info(f"User {user_id} (@{username}) sent text message: {question}")
    
    # Если пользователя нет в базе, но есть username, проверяем, не добавлен ли он по username
    if username:
        user = await db.get_user(user_id)
        if not user:
            logger.debug(f"User {user_id} (@{username}) not found in DB, checking if added by username")
            # Пытаемся обновить user_id для пользователя, добавленного по username
            success = await db.update_user_id_by_username(username, user_id)
            if success:
                logger.info(f"User {user_id} (@{username}) activated from pending users")
                # Перезагружаем данные пользователя
                user = await db.get_user(user_id)
    
    # Проверяем права доступа
    if not await db.is_user_allowed(user_id):
        logger.warning(f"User {user_id} (@{username}) tried to send text message without permission")
        await message.reply("❌ У вас нет доступа к функциям бота. Обратитесь к администратору.")
        return
    
    # Игнорируем команды (они обрабатываются отдельно)
    if message.text.startswith('/'):
        return
    
    # Очищаем текст
    question = sanitize_text(message.text)
    if not question:
        await message.reply("❌ Пустое сообщение. Задайте вопрос о вашем автомобиле.")
        return
    
    # Логируем текстовое сообщение
    await db.log_message(message.from_user.id, "text", question[:100] + "..." if len(question) > 100 else question)
    
    # Отправляем сообщение о том, что обрабатываем запрос
    processing_msg = await message.reply("🤔 Обрабатываю ваш вопрос...")
    
    try:
        # Получаем информацию о пользователе для контекста
        user = await db.get_user(message.from_user.id)
        car_info = user.get('car') if user else None
        
        # Формируем контекстный вопрос
        if car_info:
            contextual_question = f"Автомобиль пользователя: {car_info}\n\nВопрос: {question}"
        else:
            contextual_question = question
        
        # Отправляем запрос в RAG API
        from utils.rag_client import rag_client
        response = await rag_client.send_request(
            contextual_question,
            message.from_user.id,
            message.from_user.username
        )
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        if response:
            # Отправляем ответ реплаем (без реакции, так как API может быть недоступен)
            await message.reply(f"🤖 {response}", parse_mode="Markdown")
        else:
            await message.reply("⚠️ Не удалось получить ответ, попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        await message.reply("❌ Произошла ошибка при обработке вашего вопроса. Попробуйте позже.")
