from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import logging

from database.db import db
from utils.helpers import parse_command_args, validate_car_description, sanitize_text

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("set_car"))
async def cmd_set_car(message: Message):
    """Команда сохранения информации об автомобиле"""
    # Проверяем права доступа
    if not await db.is_user_allowed(message.from_user.id):
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
    contact_info = """🔧 **Запись на ТО**

Для записи на техническое обслуживание обращайтесь:

📞 **Телефон:** +7 (XXX) XXX-XX-XX
🕒 **Время работы:** Пн-Пт: 9:00-18:00, Сб: 9:00-15:00
📍 **Адрес:** [Адрес сервисного центра]

Или оставьте заявку через бота, и мы свяжемся с вами."""
    
    await message.reply(contact_info, parse_mode="Markdown")

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда старта бота"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    try:
        # Проверяем, есть ли пользователь в базе
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
• Получать советы по уходу за автомобилем""", parse_mode="Markdown")
        else:
            if user['allowed']:
                await message.reply("""👋 **Добро пожаловать в Car Assistant Bot!**

✅ **У вас есть доступ к функциям бота.**

Доступные команды:
/set_car <описание> - Сохранить информацию об автомобиле
/my_car - Показать информацию об автомобиле
/to - Записаться на ТО
/help - Справка по командам

Просто напишите любой вопрос о вашем автомобиле, и я постараюсь помочь!""", parse_mode="Markdown")
            else:
                await message.reply("""👋 **Добро пожаловать в Car Assistant Bot!**

❌ **У вас пока нет доступа к функциям бота.**
Обратитесь к администратору для получения доступа.""", parse_mode="Markdown")
                
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка текстовых сообщений (вопросы к AI)"""
    # Проверяем права доступа
    if not await db.is_user_allowed(message.from_user.id):
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
            await message.reply(f"🤖 **Ответ:**\n\n{response}", parse_mode="Markdown")
        else:
            await message.reply("⚠️ Не удалось получить ответ, попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        await message.reply("❌ Произошла ошибка при обработке вашего вопроса. Попробуйте позже.")
