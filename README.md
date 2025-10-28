# 🚗 Car Assistant Bot

Telegram-бот для владельцев автомобилей.  
Отвечает на вопросы о машине через AI (RAG API), запоминает автомобиль владельца, позволяет записываться на ТО и управляется администраторами через Telegram-команды.

---

## 🧠 Возможности

- Авторизация пользователей и ролевая модель (admin / user)
- Общение с AI (RAG API) с асинхронным ожиданием ответов
- Добавление и удаление пользователей администраторами
- Просмотр списка пользователей с фильтрацией и пагинацией
- Сохранение информации о машине пользователя
- Запись на ТО (в первой версии — контактный телефон)
- Настраиваемые параметры ожидания ответов от RAG
- Поддержка PostgreSQL для хранения данных
- Система логирования с настраиваемыми уровнями
- Статистика запросов к RAG API и сообщений пользователей
- Безопасный запуск через Docker с пользователем без root прав

---

## ⚙️ Технологический стек

- **Python 3.11+**
- **aiogram 3.2.0** - современная библиотека для Telegram Bot API
- **PostgreSQL 16** - база данных
- **asyncpg** - асинхронный драйвер PostgreSQL
- **aiohttp** - HTTP клиент для RAG API
- **Docker Compose** - контейнеризация
- **nginx + HTTPS** для продакшена

---

## 📦 Установка и запуск

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/yourname/car-assistant-bot.git
cd car-assistant-bot
```

### 2. Создайте `.env` файл
Скопируйте `env.example` в `.env` и заполните переменные:
```bash
cp env.example .env
```

Отредактируйте `.env`:
```bash
BOT_TOKEN=1234567890:ABCDEF
ADMIN_BOOTSTRAP_SECRET=nnq8522gfnlGFdsf
RAG_API_URL=https://api.sovix.ru
RAG_API_KEY=rag_sk_v1_gg5ESPZfbezZF7CdSo5RhdXQ84m7BaRnwAoak_vZPLI
RAG_POLL_INTERVAL_SEC=3
RAG_MAX_ATTEMPTS=100
DATABASE_URL=postgresql://carbot:password@postgres:5432/carbot

# Настройки логирования
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### 3. Запуск через Docker Compose
```bash
# Запуск в фоновом режиме
docker compose up -d

# Просмотр логов
docker compose logs -f bot

# Остановка
docker compose down
```

**Важно:** При запуске через Docker Compose миграции базы данных **применяются автоматически**! 
- `entrypoint.sh` ожидает готовности PostgreSQL
- Автоматически выполняет `alembic upgrade head`
- Затем запускает бота

### 4. Локальная разработка
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск PostgreSQL (через Docker)
docker run -d --name postgres \
  -e POSTGRES_USER=carbot \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=carbot \
  -p 5432:5432 \
  postgres:16

# Запуск бота
python bot.py
```

---

## 🧱 Структура проекта

```
car-assistant-bot/
│
├── bot.py                 # основной файл приложения
├── handlers/              # обработчики команд
│   ├── __init__.py
│   ├── admin.py          # команды администратора
│   └── user.py           # команды пользователей
├── database/
│   ├── db.py             # подключение к PostgreSQL
│   └── models.sql        # схема таблиц
├── alembic/              # миграции базы данных
│   ├── env.py           # настройки окружения для миграций
│   ├── script.py.mako   # шаблон для новых миграций
│   ├── README           # документация Alembic
│   └── versions/        # файлы миграций
├── utils/
│   ├── rag_client.py     # логика запросов к RAG API
│   ├── helpers.py        # парсинг аргументов, валидация
│   └── logger.py         # настройка логирования
├── logs/                 # директория для логов
├── requirements.txt
├── alembic.ini          # конфигурация Alembic
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh        # точка входа контейнера (миграции + запуск)
├── nginx.conf
├── env.example
├── start.sh             # скрипт запуска для локальной разработки
├── test_setup.py        # тестовый скрипт
├── ANALYTICS_UPDATE.md  # документация по аналитике
├── MIGRATION_GUIDE.md   # руководство по миграциям
├── .dockerignore        # исключения для Docker
├── .gitignore           # исключения для Git
└── README.md
```

---

## 🗄️ База данных

Проект использует PostgreSQL и **Alembic** для управления миграциями.

### Миграции базы данных

#### Автоматические миграции (Docker)
При запуске через Docker Compose миграции **применяются автоматически**:
1. `entrypoint.sh` ожидает готовности PostgreSQL (до 30 попыток)
2. Выполняет `alembic upgrade head`
3. При успехе запускает бота
4. При ошибке контейнер останавливается

Логи миграций можно увидеть при запуске:
```bash
docker compose up
# или
docker compose logs bot
```

#### Ручное управление миграциями
```bash
# Примените все миграции
alembic upgrade head

# Откатите последнюю миграцию
alembic downgrade -1

# Посмотрите текущий статус
alembic current

# Посмотрите историю миграций
alembic history

# Создайте новую миграцию
alembic revision -m "описание миграции"
```

### Структура таблиц

```sql
-- Основная таблица пользователей
CREATE TABLE IF NOT EXISTS users (
  user_id     BIGINT PRIMARY KEY,
  username    TEXT,
  role        TEXT,           -- 'admin' или 'user'
  allowed     BOOLEAN DEFAULT FALSE,
  car         TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
);

-- Таблица для хранения статистики запросов к RAG API
CREATE TABLE IF NOT EXISTS rag_requests (
  id          SERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL,
  request_id  TEXT,
  text        TEXT,
  status      TEXT DEFAULT 'pending', -- 'pending', 'success', 'failed'
  created_at  TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для хранения статистики сообщений
CREATE TABLE IF NOT EXISTS messages (
  id          SERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL,
  message_type TEXT NOT NULL, -- 'command', 'text', 'rag_response'
  content     TEXT,
  created_at  TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для хранения шаблонов текстов
CREATE TABLE IF NOT EXISTS text_templates (
  id          SERIAL PRIMARY KEY,
  key         TEXT UNIQUE NOT NULL,
  value       TEXT NOT NULL,
  description TEXT,
  created_at  TIMESTAMP DEFAULT NOW(),
  updated_at  TIMESTAMP DEFAULT NOW()
);

-- Таблица для логирования действий пользователей
CREATE TABLE IF NOT EXISTS user_actions_log (
  id          SERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL,
  action      TEXT NOT NULL,
  object      TEXT,
  created_at  TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для хранения информации о привлечении пользователей
CREATE TABLE IF NOT EXISTS user_acquisition (
  id             SERIAL PRIMARY KEY,
  user_id        BIGINT UNIQUE NOT NULL,
  payload_raw    TEXT,
  payload_decoded TEXT,
  src            TEXT,
  campaign       TEXT,
  ad             TEXT,
  language_code  TEXT,
  first_seen_at  TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для хранения лимитов пользователей
CREATE TABLE IF NOT EXISTS user_limits (
  id                  SERIAL PRIMARY KEY,
  user_id             BIGINT UNIQUE NOT NULL,
  absolute_limit      INTEGER DEFAULT NULL,
  absolute_used       INTEGER DEFAULT 0,
  weekly_limit        INTEGER DEFAULT NULL,
  weekly_used         INTEGER DEFAULT 0,
  week_start          TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

---

## 🔐 Авторизация и роли

- Все пользователи по умолчанию **неавторизованы**.
- Доступ к функциям — только у пользователей с `allowed = true`.
- Создание администратора:
  - команда `/bootstrap <секрет>`;
  - секрет хранится в `ADMIN_BOOTSTRAP_SECRET`;
  - при совпадении создаётся запись `role='admin'`, `allowed=true`.

---

## 💬 Команды

### Команды пользователей
| Команда | Описание |
|----------|-----------|
| `/start` | Приветствие и информация о боте |
| `/set_car <описание>` | Сохраняет автомобиль пользователя |
| `/my_car` | Показывает сохранённый автомобиль |
| `/to` | Возвращает контакт для записи на ТО |
| `/help` | Справка по командам |
| Любой другой текст | Отправляется в RAG API для получения AI-ответа |

### Команды администратора
| Команда | Описание |
|----------|-----------|
| `/bootstrap <секрет>` | Регистрирует первого администратора |
| `/add_user <id|@username>` | Добавляет пользователя по ID или username |
| `/del_user <id|@username>` | Удаляет пользователя по ID или username |
| `/list_users [фильтр] [лимит] [смещение]` | Показывает список пользователей |

### Фильтры для `/list_users`:
- `allowed` - только разрешенные пользователи
- `pending` - только ожидающие разрешения
- `admins` - только администраторы
- `users` - только обычные пользователи
- `name:<текст>` - поиск по имени пользователя

### Примеры использования:
```
/list_users                    # Все пользователи
/list_users allowed 10         # 10 разрешенных пользователей
/list_users pending 5 0        # 5 ожидающих разрешения
/list_users name:john          # Поиск по имени "john"
```

---

## 🤖 Интеграция с RAG API

### POST `/api/v1/request`
```http
POST /api/v1/request
ApiKey: <RAG_API_KEY>
Content-Type: application/json

{
  "text": "<вопрос>",
  "dialog_id": "<user_id>",
  "user_id": "<user_id>",
  "user_name": "<username>"
}
```

Ответ:
```json
{ "id": "fd2c75da-b979-49b8-a889-34e2ef7d28b0" }
```

### GET `/api/v1/request/:id`
```json
{
  "id": "fd2c75da-b979-49b8-a889-34e2ef7d28b0",
  "status": "completed",
  "response_text": "Ваш автомобиль нуждается в замене масла каждые 10 000 км."
}
```

### Логика ожидания:
- Отправка запроса через POST
- Каждые `RAG_POLL_INTERVAL_SEC` секунд выполняется GET
- При `status = completed` — ответ пользователю
- Если по истечении `RAG_MAX_ATTEMPTS` нет результата → "⚠️ Не удалось получить ответ, попробуйте позже"

---

## ⚙️ Переменные окружения

| Переменная | Назначение | Обязательная |
|-------------|------------|--------------|
| `BOT_TOKEN` | Токен Telegram-бота | ✅ |
| `ADMIN_BOOTSTRAP_SECRET` | Секрет для регистрации администратора | ✅ |
| `RAG_API_URL` | Адрес RAG API | ✅ |
| `RAG_API_KEY` | Ключ авторизации RAG | ✅ |
| `RAG_POLL_INTERVAL_SEC` | Интервал проверки статуса (сек) | ❌ (по умолчанию: 3) |
| `RAG_MAX_ATTEMPTS` | Максимум попыток ожидания | ❌ (по умолчанию: 100) |
| `DATABASE_URL` | Подключение к PostgreSQL | ✅ |
| `LOG_LEVEL` | Уровень логирования (DEBUG/INFO/WARNING/ERROR) | ❌ (по умолчанию: INFO) |
| `LOG_FORMAT` | Формат логов | ❌ (стандартный формат) |

---

## 📊 Логирование и мониторинг

### Настройка логирования
Система логирования настраивается через переменные окружения:

```bash
# Уровень детализации логов
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Формат вывода логов
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Типы логов
- **INFO** - общая информация о работе бота
- **WARNING** - предупреждения о потенциальных проблемах
- **ERROR** - ошибки, не критичные для работы
- **DEBUG** - детальная отладочная информация

### Статистика в базе данных
Бот автоматически сохраняет:
- Все запросы к RAG API в таблице `rag_requests`
- Статистику сообщений в таблице `messages`
- Информацию о пользователях и их активности

### Просмотр логов
```bash
# Логи бота в Docker
docker compose logs -f bot

# Логи с фильтрацией по уровню
docker compose logs -f bot | grep ERROR

# Логи базы данных
docker compose logs -f postgres
```

---

## 🚀 Развертывание в продакшене

### 1. Настройка SSL сертификатов
```bash
# Создайте директорию для SSL
mkdir ssl

# Получите сертификаты Let's Encrypt
certbot certonly --standalone -d your-domain.com

# Скопируйте сертификаты
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

### 2. Запуск с nginx
```bash
# Запуск только с ботом и базой данных
docker compose up -d

# Запуск с nginx (продакшен)
docker compose --profile production up -d
```

### 3. Обновление nginx.conf
Отредактируйте `nginx.conf` и замените `your-domain.com` на ваш домен.

---

## 🧭 Дальнейшее развитие

### В разработке
- [ ] Интеграция `/to` с CRM системой
- [ ] Inline-меню для администрирования
- [ ] История диалогов с пользователями
- [ ] Автоматические уведомления о ТО
- [ ] Статистика по обращениям
- [ ] Поддержка множественных автомобилей
- [ ] Интеграция с календарем для записи на ТО

### Улучшения безопасности
- [ ] Rate limiting для предотвращения спама
- [ ] Валидация входных данных
- [ ] Аудит действий администраторов
- [ ] Шифрование чувствительных данных

### Мониторинг и аналитика
- [ ] Дашборд для администраторов
- [ ] Метрики производительности
- [ ] Алерты при критических ошибках
- [ ] Экспорт статистики

---

## 🐛 Отладка

### Просмотр логов
```bash
# Логи бота
docker compose logs -f bot

# Логи базы данных
docker compose logs -f postgres

# Все логи
docker compose logs -f

# Логи с фильтрацией
docker compose logs -f bot | grep ERROR
docker compose logs -f bot | grep "User.*executed"
```

### Подключение к базе данных
```bash
# Через Docker
docker compose exec postgres psql -U carbot -d carbot

# Локально (если порт 5432 открыт)
psql -h localhost -U carbot -d carbot
```

### Полезные SQL запросы
```sql
-- Статистика пользователей
SELECT role, COUNT(*) as count FROM users GROUP BY role;

-- Последние RAG запросы
SELECT user_id, text, created_at FROM rag_requests ORDER BY created_at DESC LIMIT 10;

-- Активность пользователей
SELECT user_id, message_type, COUNT(*) as count 
FROM messages 
GROUP BY user_id, message_type 
ORDER BY count DESC;
```

### Тестирование
```bash
# Запуск тестового скрипта
python test_setup.py

# Проверка подключения к базе данных
docker compose exec postgres psql -U carbot -d carbot -c "SELECT version();"
```

---

## 👨‍💻 Авторы и лицензия

**Car Assistant Bot**  
Разработчик: команда Совикс / Патрикея  
Лицензия: MIT  
Контакт: [info@sovix.ru](mailto:info@sovix.ru)