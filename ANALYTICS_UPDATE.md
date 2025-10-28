# Обновление аналитики бота

## Изменения

### 1. База данных
- Добавлено поле `status` в таблицу `rag_requests` для отслеживания успешности/провала запросов
- Значения: `pending`, `success`, `failed`

### 2. Логирование действий
- `set_car` - установка информации о машине
- `limit_exhausted` - достижение лимита запросов

### 3. Статистика
Все поля из ТЗ теперь реализованы:
- `rag_failed` - количество неудачных RAG запросов
- `car_setted` - количество установок машин
- `limits_exhausted` - количество достижений лимитов

### 4. Команды аналитики

#### Базовая статистика
```bash
/stat [period]
# period: day (по умолчанию), month, year
```

Показывает общую статистику за период:
- Всего пользователей
- Активных пользователей
- Новых пользователей
- Сообщений (всего, команд, текстовых)
- RAG запросов (всего, неудачных)
- Установок машин
- Достижений лимитов
- Топ пользователей по активности

#### Суммаризированная статистика (CSV)
```bash
/stat users [period] csv
# Пример: /stat users day csv
```

Экспортирует CSV с полями:
- period_start
- period_end
- total_users
- active_users
- new_users
- total_messages
- command_messages
- text_messages
- rag_requests
- rag_failed
- car_setted
- limits_exhausted

#### Статистика по пользователям (CSV)
```bash
/stat users_per_day [period] csv
# Пример: /stat users_per_day month csv
```

Экспортирует CSV с полями:
- period_start
- period_end
- user_id
- username
- first_seen_at
- last_seen_at
- total_messages
- command_messages
- text_messages
- rag_requests
- rag_failed
- is_blocked
- is_admin
- car
- limits_reached
- src
- campaign
- ad
- car_setted
- limits_exhausted

## Миграция базы данных (Alembic)

Проект использует Alembic для управления миграциями базы данных.

### Автоматические миграции

При запуске через Docker Compose миграции **применяются автоматически**:
- `entrypoint.sh` ожидает готовности PostgreSQL
- Затем выполняет `alembic upgrade head`
- После успешных миграций запускает бота

Это означает, что при каждом запуске контейнера все актуальные миграции будут применены автоматически!

### Применение миграций вручную

```bash
# Установите зависимости (если еще не установлены)
pip install -r requirements.txt

# Примените все миграции
alembic upgrade head

# Или откатите последнюю миграцию
alembic downgrade -1

# Посмотрите текущий статус
alembic current

# Посмотрите историю миграций
alembic history
```

### Создание новой миграции

```bash
# Создать пустую миграцию
alembic revision -m "описание миграции"

# Миграция будет создана в alembic/versions/
```

### Структура Alembic

- `alembic.ini` - конфигурация Alembic
- `alembic/env.py` - окружение для миграций (настроено для asyncpg)
- `alembic/versions/` - директория с файлами миграций
- `alembic/script.py.mako` - шаблон для новых миграций

## Проверка работоспособности

1. Запустите бота
2. Отправьте текстовый вопрос боту
3. Установите машину через `/set_car`
4. Проверьте статистику через `/stat`
5. Экспортируйте CSV через `/stat users day csv`
6. Экспортируйте CSV по пользователям через `/stat users_per_day day csv`

Все данные должны отображаться корректно!

