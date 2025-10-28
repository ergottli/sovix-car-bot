# Руководство по миграциям базы данных

## Автоматические миграции при запуске

При запуске бота через Docker Compose миграции применяются **автоматически**:

```bash
docker compose up -d
```

### Что происходит при запуске:

1. **Ожидание базы данных** (до 60 секунд)
   - Проверка подключения к PostgreSQL каждые 2 секунды
   - Максимум 30 попыток

2. **Применение миграций**
   ```bash
   alembic upgrade head
   ```

3. **Запуск бота**
   - Если миграции прошли успешно
   - Иначе контейнер останавливается с ошибкой

### Просмотр логов миграций

```bash
# Логи в реальном времени
docker compose logs -f bot

# Все логи контейнера
docker compose logs bot

# Только ошибки
docker compose logs bot | grep ERROR
```

## Создание новой миграции

### 1. Создайте файл миграции

```bash
alembic revision -m "add_new_column_to_users"
```

Создастся файл: `alembic/versions/YYYYMMDD_HHMM_<revision_id>_add_new_column_to_users.py`

### 2. Напишите код миграции

```python
"""add new column to users

Revision ID: abc123
Revises: previous_revision
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Применение изменений."""
    op.execute("""
        ALTER TABLE users 
        ADD COLUMN phone TEXT
    """)


def downgrade() -> None:
    """Откат изменений."""
    op.execute("""
        ALTER TABLE users 
        DROP COLUMN phone
    """)
```

### 3. Примените миграцию

#### Автоматически (при следующем запуске Docker):
```bash
docker compose restart bot
```

#### Вручную (локально):
```bash
alembic upgrade head
```

#### Вручную (в работающем контейнере):
```bash
docker compose exec bot alembic upgrade head
```

## Откат миграций

### Откатить последнюю миграцию
```bash
# Локально
alembic downgrade -1

# В контейнере
docker compose exec bot alembic downgrade -1
```

### Откатить до конкретной ревизии
```bash
alembic downgrade abc123
```

### Откатить все миграции
```bash
alembic downgrade base
```

## Проверка статуса миграций

```bash
# Текущая версия БД
alembic current

# История миграций
alembic history

# История с деталями
alembic history --verbose
```

## Отладка проблем с миграциями

### Проблема: Контейнер не запускается

1. Проверьте логи:
```bash
docker compose logs bot
```

2. Проверьте подключение к БД:
```bash
docker compose exec postgres psql -U carbot -d carbot -c "SELECT version();"
```

3. Запустите миграции вручную:
```bash
docker compose exec bot alembic upgrade head
```

### Проблема: Миграция зависла

1. Проверьте текущую версию:
```bash
docker compose exec bot alembic current
```

2. Посмотрите таблицу `alembic_version`:
```bash
docker compose exec postgres psql -U carbot -d carbot -c "SELECT * FROM alembic_version;"
```

3. Если нужно, пропустите проблемную миграцию:
```bash
docker compose exec bot alembic stamp head
```

### Проблема: Конфликт версий

1. Проверьте историю:
```bash
alembic history
```

2. Создайте merge-миграцию:
```bash
alembic merge -m "merge conflict" revision1 revision2
```

## Лучшие практики

### ✅ DO (Делайте)

- Всегда тестируйте миграции локально перед деплоем
- Пишите функции `upgrade()` и `downgrade()`
- Делайте атомарные миграции (одно изменение = одна миграция)
- Проверяйте миграции на копии продакшн данных
- Используйте транзакции для безопасности

### ❌ DON'T (Не делайте)

- Не изменяйте уже применённые миграции
- Не удаляйте файлы миграций из `alembic/versions/`
- Не применяйте миграции напрямую через SQL в продакшене
- Не запускайте разные версии миграций параллельно

## Примеры миграций

### Добавление колонки
```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE users 
        ADD COLUMN email TEXT
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE users 
        DROP COLUMN email
    """)
```

### Создание таблицы
```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE notifications (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

def downgrade() -> None:
    op.execute("DROP TABLE notifications")
```

### Изменение типа колонки
```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN car TYPE TEXT
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN car TYPE VARCHAR(255)
    """)
```

### Миграция данных
```python
def upgrade() -> None:
    # Добавляем новую колонку
    op.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    
    # Мигрируем данные
    op.execute("""
        UPDATE users 
        SET full_name = username 
        WHERE full_name IS NULL
    """)

def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN full_name")
```

## Полезные команды

```bash
# Показать SQL без применения
alembic upgrade head --sql

# Показать различия
alembic show <revision>

# Проверить миграции
alembic check

# Сгенерировать автоматическую миграцию (требует SQLAlchemy models)
alembic revision --autogenerate -m "description"
```

