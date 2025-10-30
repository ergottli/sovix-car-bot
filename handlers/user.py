from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import base64
from urllib.parse import parse_qs
from datetime import datetime

from database.db import db
from utils.helpers import parse_command_args, validate_car_description, sanitize_text
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

class CarStates(StatesGroup):
    waiting_for_car_description = State()

def get_reply_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры для пользователя"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Моя машина 🚘"), KeyboardButton(text="Написать в поддержку")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или задайте вопрос"
    )
    return keyboard

async def decode_start_payload(payload: str) -> dict:
    """Декодирование payload из deep link"""
    try:
        # Декодируем base64url
        decoded = base64.urlsafe_b64decode(payload + '==')
        decoded_str = decoded.decode('utf-8')
        
        # Парсим параметры
        params = dict(parse_qs(decoded_str))
        
        # Извлекаем значения
        result = {
            'src': params.get('src', [''])[0],
            'cmp': params.get('cmp', [''])[0],
            'ad': params.get('ad', [''])[0],
            'campaign': params.get('cmp', [''])[0],  # alias
        }
        return result
    except Exception as e:
        logger.error(f"Error decoding payload: {e}")
        return {}

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start с поддержкой deep links"""
    user_id = message.from_user.id
    username = message.from_user.username
    language_code = message.from_user.language_code or 'ru'
    
    # Для /start args приходит напрямую (после пробела)
    # Если /start@botname payload, то payload в args
    # Если /start payload, то тоже в args
    payload = None
    if hasattr(message, 'text'):
        # Проверяем, есть ли аргументы после /start
        if message.text and len(message.text.split()) > 1:
            payload = message.text.split(None, 1)[1]  # Берем все после первого пробела
        elif hasattr(message, 'args') and message.args:
            # Fallback для старого метода
            payload = ' '.join(message.args) if isinstance(message.args, list) else message.args
    
    logger.info(f"Start command received for user {user_id} (@{username}), payload: {payload}, full text: {message.text}")
    
    acquisition_data = {}
    if payload:
        # Декодируем payload
        acquisition_data = await decode_start_payload(payload)
        logger.info(f"Decoded acquisition data for user {user_id}: {acquisition_data}")
    
    try:
        # Проверяем, есть ли пользователь с временным ID по username
        if username:
            # Нормализуем username - всегда храним с @
            normalized_username = f"@{username.lstrip('@')}"
            
            async with db.pool.acquire() as conn:
                temp_user = await conn.fetchrow("""
                    SELECT user_id, role, allowed FROM users 
                    WHERE username = $1 AND user_id < 0
                """, normalized_username)
                
                if temp_user:
                    # Обновляем временный ID на реальный
                    await conn.execute("""
                        DELETE FROM users WHERE user_id = $1
                    """, temp_user['user_id'])
                    
                    await conn.execute("""
                        INSERT INTO users (user_id, username, role, allowed)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (user_id) DO UPDATE 
                        SET username = EXCLUDED.username, role = EXCLUDED.role, allowed = EXCLUDED.allowed
                    """, user_id, normalized_username, temp_user['role'], temp_user['allowed'])
                    
                    logger.info(f"User {user_id} ({normalized_username}) activated from temporary ID {temp_user['user_id']}")
                else:
                    # Добавляем пользователя обычным способом
                    await db.add_user(user_id, username)
        else:
            # Если нет username, просто добавляем пользователя
            await db.add_user(user_id, username or f"user_{user_id}")
        
        # Сохраняем информацию о привлечении если есть
        if acquisition_data and (acquisition_data.get('src') or acquisition_data.get('campaign')):
            logger.info(f"Saving acquisition data for user {user_id}: src={acquisition_data.get('src')}, campaign={acquisition_data.get('campaign')}, ad={acquisition_data.get('ad')}")
            await db.save_user_acquisition(
                user_id=user_id,
                payload_raw=payload,
                payload_decoded=str(acquisition_data),
                src=acquisition_data.get('src', ''),
                campaign=acquisition_data.get('campaign', ''),
                ad=acquisition_data.get('ad', ''),
                language_code=language_code
            )
        else:
            if payload:
                logger.warning(f"Payload present but acquisition_data is empty for user {user_id}. Payload: {payload[:100]}")
            else:
                logger.info(f"No payload for user {user_id}, acquisition data not saved")
        
        # Логируем действие
        await db.log_action(user_id, "start", payload)
        
        # Получаем приветственный текст из шаблона
        welcome_text = await db.get_template('welcome_text')
        if not welcome_text:
            welcome_text = "Привет! Я твой помощник по китайским машинам — помогу с эксплуатацией, ТО, ошибками и советами."
        
        await message.reply(welcome_text, reply_markup=get_reply_keyboard(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "Моя машина 🚘")
async def my_car_menu(message: Message):
    """Обработка кнопки 'Моя машина'"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    user = await db.get_user(user_id)
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    # Логируем действие
    await db.log_action(user_id, "menu_action", "my_car")
    
    try:
        car_info = await db.get_car(user_id)
        if car_info:
            response = f"""🚗 <b>Ваш автомобиль:</b>
{car_info}

Что вы хотите сделать?
• /set_car - изменить автомобиль
• /delete_car - удалить информацию об автомобиле
"""
            await message.reply(response, parse_mode="HTML")
        else:
            response = """🚗 У вас не указан автомобиль.

Добавьте информацию о вашем автомобиле командой:
/set_car"""
            await message.reply(response, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in my_car_menu: {e}")
        await message.reply("❌ Произошла ошибка.")

@router.message(F.text == "Написать в поддержку")
async def support_menu(message: Message):
    """Обработка кнопки 'Написать в поддержку'"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    user = await db.get_user(user_id)
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    # Логируем действие
    await db.log_action(user_id, "menu_action", "support")
    
    # Получаем текст из шаблона
    support_text = await db.get_template('support_text')
    if not support_text:
        support_text = "Поддержка готова помочь с вашим вопросом, пишите https://t.me/PerovV12"
    
    await message.reply(support_text)

@router.message(Command("support"))
async def cmd_support(message: Message):
    """Команда обращения в поддержку"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    user = await db.get_user(user_id)
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    # Логируем действие
    await db.log_action(user_id, "support_command")
    
    # Получаем текст из шаблона
    support_text = await db.get_template('support_text')
    if not support_text:
        support_text = "Поддержка готова помочь с вашим вопросом, пишите https://t.me/PerovV12"
    
    await message.reply(support_text)

@router.message(Command("my_car"))
async def cmd_my_car(message: Message):
    """Команда просмотра своего автомобиля"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    user = await db.get_user(user_id)
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    # Логируем действие
    await db.log_action(user_id, "my_car")
    
    try:
        car_info = await db.get_car(user_id)
        if car_info:
            response = f"""🚗 <b>Ваш автомобиль:</b>
{car_info}

Что вы хотите сделать?
• /set_car - изменить автомобиль
• /delete_car - удалить информацию об автомобиле
"""
            await message.reply(response, parse_mode="HTML")
        else:
            response = """🚗 У вас не указан автомобиль.

Добавьте информацию о вашем автомобиле командой:
/set_car"""
            await message.reply(response, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in my_car: {e}")
        await message.reply("❌ Произошла ошибка.")

@router.message(Command("delete_car"))
async def cmd_delete_car(message: Message):
    """Команда удаления информации об автомобиле"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    user = await db.get_user(user_id)
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    # Логируем действие
    await db.log_action(user_id, "delete_car")
    
    try:
        await db.set_car(user_id, None)
        await message.reply("✅ Информация об автомобиле удалена.")
    except Exception as e:
        logger.error(f"Error deleting car: {e}")
        await message.reply("❌ Произошла ошибка при удалении информации.")

@router.message(Command("set_car"))
async def cmd_set_car(message: Message, state: FSMContext):
    """Команда сохранения информации об автомобиле"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    user = await db.get_user(user_id)
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    # Логируем действие
    await db.log_action(user_id, "set_car_start", "car")
    
    # Переходим в состояние ожидания описания машины
    await state.set_state(CarStates.waiting_for_car_description)
    await message.reply("🚗 Отлично! Введите описание вашего автомобиля.\n\nНапример: Chery Tiggo 7 Pro 2021\n\nДля отмены введите /cancel")

@router.message(Command("cancel"), CarStates.waiting_for_car_description)
async def cancel_car_input(message: Message, state: FSMContext):
    """Отмена ввода описания автомобиля"""
    await state.clear()
    await message.reply("❌ Ввод описания автомобиля отменён.")

@router.message(CarStates.waiting_for_car_description)
async def process_car_description(message: Message, state: FSMContext):
    """Обработка введённого описания автомобиля"""
    user_id = message.from_user.id
    
    car_description = sanitize_text(message.text)
    
    # Валидируем описание
    if not validate_car_description(car_description):
        await message.reply("❌ Описание автомобиля слишком короткое. Минимум 3 символа.\n\nПопробуйте ещё раз:")
        return
    
    try:
        await db.set_car(user_id, car_description)
        await db.log_message(user_id, "command", f"set_car: {car_description[:100]}...")
        await db.log_action(user_id, "set_car", car_description[:100])
        await message.reply(f"✅ Информация об автомобиле сохранена:\n🚗 {car_description}")
        
        # Очищаем состояние
        await state.clear()
    except Exception as e:
        logger.error(f"Error setting car: {e}")
        await message.reply("❌ Произошла ошибка при сохранении информации об автомобиле.")
        await state.clear()

@router.message(F.photo | F.video | F.audio | F.voice | F.document | F.sticker | F.video_note)
async def handle_media_message(message: Message):
    """Обработка медиа сообщений (фото, видео, аудио и т.д.)"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    user = await db.get_user(user_id)
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    # Логируем действие
    media_type = "unknown"
    if message.photo:
        media_type = "photo"
    elif message.video:
        media_type = "video"
    elif message.audio:
        media_type = "audio"
    elif message.voice:
        media_type = "voice"
    elif message.document:
        media_type = "document"
    elif message.sticker:
        media_type = "sticker"
    elif message.video_note:
        media_type = "video_note"
    
    await db.log_action(user_id, "media_message", media_type)
    await db.log_message(user_id, "media", media_type)
    
    # Получаем текст из шаблона
    media_text = await db.get_template('media_not_supported_text')
    if not media_text:
        media_text = "Напишите свой вопрос. Картинки и аудио я пока не понимаю, но уже учусь)"
    
    await message.reply(media_text)

@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка текстовых сообщений (вопросы к боту)"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Игнорируем команды (они обрабатываются отдельно)
    if message.text.startswith('/'):
        return
    
    # Добавляем пользователя в базу если его еще нет, или активируем с временного ID
    user = await db.get_user(user_id)
    if not user and username:
        # Нормализуем username - всегда храним с @
        normalized_username = f"@{username.lstrip('@')}"
        
        # Проверяем, есть ли пользователь с временным ID
        async with db.pool.acquire() as conn:
            temp_user = await conn.fetchrow("""
                SELECT user_id, role, allowed FROM users 
                WHERE username = $1 AND user_id < 0
            """, normalized_username)
            
            if temp_user:
                # Обновляем временный ID на реальный
                await conn.execute("""
                    DELETE FROM users WHERE user_id = $1
                """, temp_user['user_id'])
                
                await conn.execute("""
                    INSERT INTO users (user_id, username, role, allowed)
                    VALUES ($1, $2, $3, $4)
                """, user_id, normalized_username, temp_user['role'], temp_user['allowed'])
                
                logger.info(f"User {user_id} ({normalized_username}) activated from temporary ID {temp_user['user_id']}")
                user = await db.get_user(user_id)
            else:
                await db.add_user(user_id, username or f"user_{user_id}")
                user = await db.get_user(user_id)
    elif not user:
        await db.add_user(user_id, username or f"user_{user_id}")
        user = await db.get_user(user_id)
    
    # Проверяем, не заблокирован ли пользователь
    if user and not user.get('allowed'):
        await message.reply("❌ Ваш доступ к функциям бота заблокирован администратором.")
        return
    
    question = sanitize_text(message.text)
    if not question:
        await message.reply("❌ Пустое сообщение. Задайте вопрос о вашем автомобиле.")
        return
    
    # Логируем текстовое сообщение
    await db.log_action(user_id, "text_question", question[:100])
    await db.log_message(user_id, "text", question[:100])
    
    # Проверяем лимиты
    can_proceed, error = await db.check_and_increment_limits(user_id)
    
    if not can_proceed:
        await db.log_action(user_id, "limit_exhausted", error)
        limit_message = await db.get_template('limit_exceeded_text')
        if not limit_message:
            limit_message = "Превышен лимит вопросов"
        await message.reply(limit_message)
        return
    
    # Отправляем сообщение о том, что обрабатываем запрос
    processing_text = await db.get_template('processing_text')
    if not processing_text:
        processing_text = "🤔 Обрабатываю ваш вопрос..."
    
    processing_msg = await message.reply(processing_text)
    
    try:
        # Получаем информацию о пользователе для контекста
        user = await db.get_user(user_id)
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
            user_id,
            username
        )
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        if response:
            # Отправляем ответ реплаем
            await message.reply(f"{response}")
        else:
            error_text = await db.get_template('rag_error_text')
            if not error_text:
                error_text = "⚠️ Не удалось получить ответ, попробуйте позже."
            await message.reply(error_text)
            
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        
        error_text = await db.get_template('rag_error_text')
        if not error_text:
            error_text = "⚠️ Не удалось получить ответ, попробуйте позже."
        await message.reply(error_text)
