-- Хранит изменяемые без перезапуска параметры фоновых процессов Яндекс Маркета.

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_runtime_settings (
    singleton_id smallint PRIMARY KEY DEFAULT 1 CHECK (singleton_id = 1),
    daily_limit_poll_interval_sec integer NOT NULL DEFAULT 15
        CHECK (daily_limit_poll_interval_sec BETWEEN 5 AND 3600),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO app.marketplace_yandex_runtime_settings (
    singleton_id,
    daily_limit_poll_interval_sec
)
VALUES (1, 15)
ON CONFLICT (singleton_id) DO NOTHING;
