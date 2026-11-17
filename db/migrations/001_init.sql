-- CookieKub / KubanoID — базовая схема PostgreSQL 17
-- Деньги хранятся в копейках (INTEGER), время — TIMESTAMPTZ.

CREATE SEQUENCE IF NOT EXISTS order_number_seq START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------- Пользователи KubanoID ----------
CREATE TABLE IF NOT EXISTS users (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email               TEXT        NOT NULL,
    password_hash       TEXT        NOT NULL,
    full_name           TEXT        NOT NULL DEFAULT '',
    role                TEXT        NOT NULL DEFAULT 'user'
                        CHECK (role IN ('user', 'admin')),
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    privacy_consent_at  TIMESTAMPTZ,
    anonymized_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Сессии (непрозрачные токены, в БД только sha256) ----------
CREATE TABLE IF NOT EXISTS sessions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    token_hash  TEXT        NOT NULL UNIQUE,
    user_id     BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Товары ----------
CREATE TABLE IF NOT EXISTS products (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug               TEXT        NOT NULL UNIQUE,
    name               TEXT        NOT NULL,
    short_description  TEXT        NOT NULL DEFAULT '',
    description        TEXT        NOT NULL DEFAULT '',
    price_cents        INTEGER     NOT NULL CHECK (price_cents > 0),
    image_url          TEXT        NOT NULL DEFAULT '',
    category           TEXT        NOT NULL DEFAULT 'classic',
    stock_qty          INTEGER     NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    is_active          BOOLEAN     NOT NULL DEFAULT TRUE,
    sort_order         INTEGER     NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Промокоды ----------
CREATE TABLE IF NOT EXISTS promos (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code             TEXT        NOT NULL,
    discount_type    TEXT        NOT NULL CHECK (discount_type IN ('percent', 'fixed')),
    percent_value    INTEGER     CHECK (percent_value BETWEEN 1 AND 100),
    amount_cents     INTEGER     CHECK (amount_cents > 0),
    min_order_cents  INTEGER     NOT NULL DEFAULT 0 CHECK (min_order_cents >= 0),
    max_uses         INTEGER     CHECK (max_uses > 0),
    used_count       INTEGER     NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    starts_at        TIMESTAMPTZ,
    ends_at          TIMESTAMPTZ,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT promos_type_values CHECK (
        (discount_type = 'percent' AND percent_value IS NOT NULL AND amount_cents IS NULL)
        OR
        (discount_type = 'fixed' AND amount_cents IS NOT NULL AND percent_value IS NULL)
    ),
    CONSTRAINT promos_used_count_limit CHECK (max_uses IS NULL OR used_count <= max_uses),
    CONSTRAINT promos_period CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at)
);

-- ---------- Кафе ----------
CREATE TABLE IF NOT EXISTS cafes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug        TEXT        NOT NULL UNIQUE,
    name        TEXT        NOT NULL,
    address     TEXT        NOT NULL,
    phone       TEXT        NOT NULL DEFAULT '',
    opens_at    TIME        NOT NULL,
    closes_at   TIME        NOT NULL,
    map_x       NUMERIC(5, 2) NOT NULL CHECK (map_x BETWEEN 0 AND 100),
    map_y       NUMERIC(5, 2) NOT NULL CHECK (map_y BETWEEN 0 AND 100),
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    sort_order  INTEGER     NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Заказы ----------
CREATE TABLE IF NOT EXISTS orders (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_number        TEXT        NOT NULL UNIQUE,
    user_id             BIGINT      REFERENCES users(id) ON DELETE SET NULL,
    customer_name       TEXT        NOT NULL,
    customer_email      TEXT        NOT NULL,
    customer_phone      TEXT        NOT NULL DEFAULT '',
    customer_comment    TEXT        NOT NULL DEFAULT '',
    fulfillment         TEXT        NOT NULL CHECK (fulfillment IN ('pickup', 'delivery')),
    cafe_id             BIGINT      REFERENCES cafes(id) ON DELETE SET NULL,
    delivery_address    TEXT,
    status              TEXT        NOT NULL DEFAULT 'processing'
                        CHECK (status IN ('processing', 'completed', 'cancelled')),
    subtotal_cents      INTEGER     NOT NULL CHECK (subtotal_cents >= 0),
    discount_cents      INTEGER     NOT NULL DEFAULT 0 CHECK (discount_cents >= 0),
    total_cents         INTEGER     NOT NULL CHECK (total_cents >= 0),
    promo_id            BIGINT      REFERENCES promos(id) ON DELETE SET NULL,
    promo_code          TEXT,
    payment_ref         TEXT,
    card_last4          TEXT        CHECK (card_last4 IS NULL OR card_last4 ~ '^[0-9]{4}$'),
    privacy_consent_at  TIMESTAMPTZ,
    paid_at             TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT orders_totals CHECK (total_cents = subtotal_cents - discount_cents),
    CONSTRAINT orders_discount_cap CHECK (discount_cents <= subtotal_cents),
    CONSTRAINT orders_fulfillment_fields CHECK (
        (fulfillment = 'pickup' AND cafe_id IS NOT NULL AND delivery_address IS NULL)
        OR
        (fulfillment = 'delivery' AND delivery_address IS NOT NULL AND cafe_id IS NULL)
    ),
    CONSTRAINT orders_completed_at CHECK (status <> 'completed' OR completed_at IS NOT NULL)
);

-- ---------- Позиции заказа (снимок названия/цены) ----------
CREATE TABLE IF NOT EXISTS order_items (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id         BIGINT  NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id       BIGINT  REFERENCES products(id) ON DELETE SET NULL,
    product_name     TEXT    NOT NULL,
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    quantity         INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 99),
    line_total_cents INTEGER NOT NULL CHECK (line_total_cents > 0),
    CONSTRAINT order_items_line_total CHECK (line_total_cents = unit_price_cents * quantity)
);

-- ---------- Применения промокодов ----------
CREATE TABLE IF NOT EXISTS promo_redemptions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    promo_id    BIGINT NOT NULL REFERENCES promos(id) ON DELETE CASCADE,
    order_id    BIGINT NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Тикеты поддержки ----------
CREATE TABLE IF NOT EXISTS tickets (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    email        TEXT        NOT NULL,
    subject      TEXT        NOT NULL,
    category     TEXT        NOT NULL DEFAULT 'other'
                 CHECK (category IN ('bug', 'question', 'other')),
    message      TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open', 'answered', 'closed')),
    admin_reply  TEXT,
    replied_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Аудит действий администраторов ----------
CREATE TABLE IF NOT EXISTS admin_audit (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_user_id  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action         TEXT        NOT NULL,
    entity_type    TEXT        NOT NULL,
    entity_id      TEXT        NOT NULL,
    details        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Версии миграций ----------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Триггеры updated_at ----------
DROP TRIGGER IF EXISTS users_set_updated_at ON users;
CREATE TRIGGER users_set_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS products_set_updated_at ON products;
CREATE TRIGGER products_set_updated_at BEFORE UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS promos_set_updated_at ON promos;
CREATE TRIGGER promos_set_updated_at BEFORE UPDATE ON promos
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS cafes_set_updated_at ON cafes;
CREATE TRIGGER cafes_set_updated_at BEFORE UPDATE ON cafes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS orders_set_updated_at ON orders;
CREATE TRIGGER orders_set_updated_at BEFORE UPDATE ON orders
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS tickets_set_updated_at ON tickets;
CREATE TRIGGER tickets_set_updated_at BEFORE UPDATE ON tickets
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE users IS 'Аккаунты KubanoID; пароль — scrypt-хэш, PII минимизированы';
COMMENT ON TABLE sessions IS 'Непрозрачные сессии; хранится только sha256 токена';
COMMENT ON TABLE orders IS 'Заказы; user_id NULL = гостевой заказ; card_last4 — максимум платёжных данных';
COMMENT ON TABLE admin_audit IS 'Журнал действий админов; details без PII';
