-- Индексы и ограничения по регистру для CookieKub

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uidx
    ON users (lower(email));

CREATE UNIQUE INDEX IF NOT EXISTS promos_code_lower_uidx
    ON promos (upper(code));

CREATE INDEX IF NOT EXISTS sessions_expires_idx
    ON sessions (expires_at);

CREATE INDEX IF NOT EXISTS sessions_user_idx
    ON sessions (user_id);

CREATE INDEX IF NOT EXISTS products_active_sort_idx
    ON products (is_active, sort_order, id);

CREATE INDEX IF NOT EXISTS products_category_idx
    ON products (category);

CREATE INDEX IF NOT EXISTS orders_customer_email_lower_idx
    ON orders (lower(customer_email));

CREATE INDEX IF NOT EXISTS orders_status_paid_idx
    ON orders (status, paid_at);

CREATE INDEX IF NOT EXISTS orders_user_created_idx
    ON orders (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS orders_created_idx
    ON orders (created_at DESC);

CREATE INDEX IF NOT EXISTS order_items_order_idx
    ON order_items (order_id);

CREATE INDEX IF NOT EXISTS promo_redemptions_promo_idx
    ON promo_redemptions (promo_id);

CREATE INDEX IF NOT EXISTS promo_redemptions_user_idx
    ON promo_redemptions (user_id);

CREATE INDEX IF NOT EXISTS tickets_status_created_idx
    ON tickets (status, created_at DESC);

CREATE INDEX IF NOT EXISTS tickets_email_lower_idx
    ON tickets (lower(email));

CREATE INDEX IF NOT EXISTS admin_audit_created_idx
    ON admin_audit (created_at DESC);

CREATE INDEX IF NOT EXISTS admin_audit_actor_idx
    ON admin_audit (actor_user_id);
