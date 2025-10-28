# 📊 Статистика и аналитика

## Команды статистики

### Базовая статистика
```bash
/stat [период]
```

Показывает текстовую статистику за период (без экспорта):
- `day` - за день (по умолчанию)
- `month` - за месяц (30 дней)
- `year` - за год (365 дней)

**Примеры:**
```bash
/stat day
/stat month
/stat year
```

### CSV экспорт - Суммаризация
```bash
/stat users [период] csv
```

Экспортирует **сводную статистику** в CSV файл.

**Структура CSV:**
```
period_start, period_end, total_users, active_users, new_users,
total_messages, command_messages, text_messages, rag_requests,
rag_failed, car_setted, limits_exhausted
```

**Примеры:**
```bash
/stat users day csv       # За день
/stat users month csv     # За месяц
/stat users year csv      # За год
```

### CSV экспорт - По пользователям
```bash
/stat users_per_day [период] csv
```

Экспортирует **детальную статистику по каждому пользователю** в CSV файл.

**Структура CSV:**
```
period_start, period_end, user_id, username, first_seen_at, last_seen_at,
total_messages, command_messages, text_messages, rag_requests, rag_failed,
is_blocked, is_admin, car, limits_reached, src, campaign, ad,
car_setted, limits_exhausted
```

**Примеры:**
```bash
/stat users_per_day day csv    # За день
/stat users_per_day month csv  # За месяц
/stat users_per_day year csv   # За год
```

## Описание полей

### Суммаризированная статистика

| Поле | Описание |
|------|----------|
| `period_start` | Начало периода |
| `period_end` | Конец периода |
| `total_users` | Всего пользователей в системе |
| `active_users` | Пользователей, активных за период |
| `new_users` | Новых пользователей за период |
| `total_messages` | Всего сообщений за период |
| `command_messages` | Команд за период |
| `text_messages` | Текстовых сообщений за период |
| `rag_requests` | RAG запросов за период |
| `rag_failed` | Неудачных RAG запросов |
| `car_setted` | Установок машин за период |
| `limits_exhausted` | Достижений лимитов за период |

### Статистика по пользователям

| Поле | Описание |
|------|----------|
| `period_start` | Начало периода |
| `period_end` | Конец периода |
| `user_id` | ID пользователя Telegram |
| `username` | Username пользователя |
| `first_seen_at` | Дата первого обращения |
| `last_seen_at` | Дата последнего обращения |
| `total_messages` | Всего сообщений |
| `command_messages` | Команд |
| `text_messages` | Текстовых сообщений |
| `rag_requests` | RAG запросов |
| `rag_failed` | Неудачных RAG запросов |
| `is_blocked` | Заблокирован (true/false) |
| `is_admin` | Администратор (true/false) |
| `car` | Информация о машине |
| `limits_reached` | Лимит достигнут (true/false) |
| `src` | Источник привлечения |
| `campaign` | Кампания |
| `ad` | Объявление |
| `car_setted` | Установок машин |
| `limits_exhausted` | Достижений лимитов |

## Использование CSV

### Открытие в Excel/LibreOffice
1. Получите CSV файл через команду
2. Откройте в Excel или LibreOffice Calc
3. Установите кодировку UTF-8
4. Разделитель: запятая (`,`)

### Открытие в Python
```python
import csv
import pandas as pd

# Загрузить CSV
df = pd.read_csv('stat_users_day.csv')

# Показать данные
print(df.head())
```

### Загрузка в Google Sheets
1. Получите CSV файл
2. Google Sheets → Файл → Импортировать
3. Выберите файл
4. Кодировка: UTF-8

## Логика периода

### day (1 день)
- Период: последние 24 часа от текущего момента
- Используется по умолчанию

### month (30 дней)
- Период: последние 30 дней от текущего момента
- Месяц = 30 дней (не календарный месяц)

### year (365 дней)
- Период: последние 365 дней от текущего момента
- Год = 365 дней

## Права доступа

- ✅ Только администраторы могут использовать команды статистики
- ✅ Текущий пользователь: проверяется через `is_admin()`
- ❌ Обычные пользователи получают сообщение об отказе в доступе

## Обработка ошибок

### Ошибка подключения к БД
```
❌ Произошла ошибка при экспорте статистики.
```
- Проверьте доступность PostgreSQL
- Проверьте переменную `DATABASE_URL` в `.env`

### Нет данных в CSV
- Файл все равно будет создан
- В CSV будет только заголовок без строк данных

### Большие CSV файлы
- Для больших периодов файлы могут быть большими
- Telegram ограничивает размер файлов до 50 МБ
- При превышении бот отправит ошибку

## Примечания

- ⏰ Время в CSV: UTC
- 📊 Пустые поля: пустые ячейки (not NULL)
- 🎯 Метки времени: формат `YYYY-MM-DD HH:MM:SS`
- 📈 Булевы значения: `True` / `False` (Python format)

