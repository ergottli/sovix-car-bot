CREATE TABLE IF NOT EXISTS users (
  user_id     BIGINT PRIMARY KEY,
  username    TEXT,
  role        TEXT,           -- 'admin' или 'user'
  allowed     BOOLEAN DEFAULT FALSE,
  car         TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
);
