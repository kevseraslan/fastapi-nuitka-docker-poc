-- ==================================================================
-- FastAPI + Nuitka PoC - Veritabani Ilk Kurulum Semasi (init.sql)
-- ==================================================================
-- Bu betik, PostgreSQL konteyneri ilk kez calistirildiginda 
-- '/docker-entrypoint-initdb.d/init.sql' uzerinden otomatik yurutulur.
-- NOT: Yalnizca bos veritabani baslatilirken calisir; mevcut veritabani
-- varsa Docker bu betigi tekrar calistirmaz.

-- 1. Users Tablosu
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. Refresh Tokens Tablosu
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE
);

-- Refresh tokens id indeksi
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_id ON refresh_tokens (id);

-- 3. Alembic Versiyon Tablosu (Gelecekteki goclere uyumluluk icin)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

-- Baslangic migration versiyon kaydi
INSERT INTO alembic_version (version_num) 
VALUES ('25ebd001e607') 
ON CONFLICT (version_num) DO NOTHING;
