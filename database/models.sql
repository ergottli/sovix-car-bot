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
