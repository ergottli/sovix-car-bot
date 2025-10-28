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

-- Таблица для хранения информации о привлечении пользователей (рекламные источники)
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
  absolute_limit      INTEGER DEFAULT NULL,  -- Абсолютный лимит (NULL = безлимит)
  absolute_used       INTEGER DEFAULT 0,      -- Использовано абсолютных запросов
  weekly_limit        INTEGER DEFAULT NULL,   -- Недельный лимит (NULL = безлимит)
  weekly_used         INTEGER DEFAULT 0,      -- Использовано недельных запросов
  week_start          TIMESTAMP DEFAULT NOW(), -- Начало недели для отсчета
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
