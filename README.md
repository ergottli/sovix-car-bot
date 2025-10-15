# 🚗 Car Assistant Bot

Telegram-бот для владельцев автомобилей.  
Отвечает на вопросы о машине через AI (RAG API), запоминает автомобиль владельца, позволяет записываться на ТО и управляется администраторами через Telegram-команды.

---

## 🧠 Возможности

- Авторизация пользователей и ролевая модель (admin / user)
- Общение с AI (RAG API)
- Добавление и удаление пользователей
- Просмотр списка пользователей
- Сохранение информации о машине
- Запись на ТО (в первой версии — контактный телефон)
- Настраиваемые параметры ожидания ответов от RAG
- Поддержка PostgreSQL для хранения данных

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
├── utils/
│   ├── rag_client.py     # логика запросов к RAG API
│   └── helpers.py        # парсинг аргументов, валидация
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── env.example
├── .gitignore
└── README.md
```

---

## 🗄️ База данных

```sql
CREATE TABLE IF NOT EXISTS users (
  user_id     BIGINT PRIMARY KEY,
  username    TEXT,
  role        TEXT,           -- 'admin' или 'user'
  allowed     BOOLEAN DEFAULT FALSE,
  car         TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
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
| `/add_user <id>` | Добавляет пользователя |
| `/del_user <id>` | Удаляет пользователя |
| `/list_users [фильтр] [лимит] [смещение]` | Показывает список пользователей |

### Фильтры для `/list_users`:
- `allowed` - только разрешенные пользователи
- `pending` - только ожидающие разрешения
- `admins` - только администраторы
- `users` - только обычные пользователи
- `name:<текст>` - поиск по имени пользователя

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

- [ ] Интеграция `/to` с CRM системой
- [ ] Inline-меню для администрирования
- [ ] История диалогов с пользователями
- [ ] Автоматические уведомления о ТО
- [ ] Статистика по обращениям
- [ ] Поддержка множественных автомобилей
- [ ] Интеграция с календарем для записи на ТО

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
```

### Подключение к базе данных
```bash
# Через Docker
docker compose exec postgres psql -U carbot -d carbot

# Локально (если порт 5432 открыт)
psql -h localhost -U carbot -d carbot
```

---

## 👨‍💻 Авторы и лицензия

**Car Assistant Bot**  
Разработчик: команда Совикс / Патрикея  
Лицензия: MIT  
Контакт: [info@sovix.ru](mailto:info@sovix.ru)