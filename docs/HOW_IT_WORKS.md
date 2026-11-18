# CookieKub — как устроен сайт и что происходит внутри

Это учебный симулятор пекарни. Реальных денег, доставки и писем нет: оплата имитируется, статус заказа меняется по таймеру, письмо поддержки не отправляется. Но архитектура, база данных, авторизация и API — настоящие.

Документ отвечает на вопросы:

- из каких частей состоит сайт и где что запущено;
- какие запросы летят при входе, заказе, завершении заказа и удалении аккаунта;
- где хранятся заказы, пользователи, корзина и токены;
- используются ли cookie, пароли и ключи;
- что именно лежит в PostgreSQL, а что — в браузере.

Секреты и пароли в этом файле не дублируются: они собраны в `CookieKub_ПОЛНАЯ_ИНФОРМАЦИЯ.md` (лежит рядом с проектом, в git не входит).

---

## 1. Коротко: три части и одна база

```
Браузер
  │
  ├── HTML/CSS/JS  ←  GitHub Pages
  │     https://rikkahatsune.github.io/cookiekub/
  │
  └── fetch /api/*  →  Flask API на Vercel
                        https://cookiekub.vercel.app
                              │
                              └── psycopg → PostgreSQL в Supabase
                                             (11 таблиц)
```

| Часть | Где работает | Что делает | Что хранит |
|---|---|---|---|
| Фронтенд | GitHub Pages | страницы, стили, JS, корзина, вызовы API | `localStorage`: корзина, токен, история гостевых заказов |
| API | Vercel (Python/Flask) | бизнес-логика, авторизация, заказы, админка | ничего постоянно; на время запроса — соединение с БД |
| База | Supabase (PostgreSQL) | пользователи, сессии, товары, заказы, промокоды, кафе, тикеты, аудит | все постоянные данные |
| Репозиторий | GitHub | исходники, CI, деплой Pages | код, миграции, документация |

GitHub Pages умеет отдавать только статические файлы. Поэтому он не может сам выполнить Python-код или подключиться к PostgreSQL. Все действия с данными идут через Flask API на Vercel.

Почему в итоге Vercel и Supabase: изначально планировались Render (API) и Neon (БД), но оба сервиса блокируются в РФ. Поэтому фактический стек — Vercel для Flask и Supabase для PostgreSQL.

---

## 2. Где какие данные лежат

### 2.1. В PostgreSQL (Supabase)

Основные таблицы:

| Таблица | Что хранит |
|---|---|
| `users` | email, scrypt-хеш пароля, имя, роль (`user`/`admin`), флаг активности, согласие на ПД, дата анонимизации |
| `sessions` | `sha256` токена сессии, user_id, срок жизни (7 дней) |
| `products` | 12 печенек: slug, название, описание, цена в копейках, остаток, категория, картинка |
| `cafes` | 3 точки самовывоза: адрес, телефон, часы, координаты на карте |
| `promos` | промокоды: процент/фикс, минимальная сумма, лимит использований, сроки |
| `orders` | заказ: номер, user_id (NULL для гостя), имя/email/телефон, способ получения, кафе или адрес, статус, суммы, промокод, платёжная ссылка, last4, даты |
| `order_items` | состав заказа: товар, название и цена на момент покупки, количество, сумма строки |
| `promo_redemptions` | факт применения промокода к заказу (`order_id` уникален) |
| `tickets` | обращения в поддержку: тема, категория, сообщение, статус, ответ админа |
| `admin_audit` | журнал действий админа: кто, что, когда, JSONB-детали |
| `schema_migrations` | какие миграции применены |

Деньги везде в **копейках** (`INTEGER`), чтобы не ловить ошибки округления float. Например, 149 ₽ — это `14900`.

Заказ гостя: `orders.user_id = NULL`, но `customer_email` обязателен. Заказ пользователя: `user_id` заполнен, а email принудительно берётся из аккаунта.

### 2.2. В браузере (`localStorage`)

| Ключ | Что внутри | Когда появляется |
|---|---|---|
| `cookiekub.cart.v1` | массив `{product_id, quantity}` | при добавлении в корзину |
| `cookiekub.token` | токен сессии KubanoID | после входа/регистрации |
| `cookiekub.guestOrders.v1` | последние 20 гостевых заказов (номер + email) | после гостевого заказа |

Это **не cookie**. `localStorage` живёт в браузере, доступен только JS этого сайта и отправляется на сервер только вручную — в заголовке `Authorization`.

Cookie для авторизации **не используются вообще**. Поэтому:

- нет `Set-Cookie` и `Cookie` в запросах;
- нет CSRF-токена — потому что нет автоматической отправки cookie;
- токен нужно явно положить в `Authorization: Bearer <token>`.

### 2.3. В переменных окружения Vercel

| Переменная | Зачем |
|---|---|
| `DATABASE_URL` | строка подключения к Supabase (включая пароль БД) |
| `SECRET_KEY` | стандартная настройка Flask |
| `MAINTENANCE_TOKEN` | токен для служебной очистки старых данных |
| `SUPPORT_EMAIL` | адрес поддержки |
| `APP_ENV` | `production` |
| `ORDER_COMPLETE_DELAY_SECONDS` | задержка автозавершения заказа, по умолчанию 60 |
| `SESSION_TTL_DAYS` | срок сессии, по умолчанию 7 |
| `CORS_ORIGINS` | список разрешённых origin: GitHub Pages и Vercel |
| `RATE_LIMIT_ENABLED` | включает лимиты запросов |

Значения этих переменных не лежат в git. Локально для разработки используется `.env`, на Vercel — Environment Variables проекта.

### 2.4. В GitHub

- исходники фронтенда и бэкенда;
- SQL-миграции `db/migrations/001_init.sql`, `002_indexes.sql`;
- workflow `.github/workflows/pages.yml` — публикует `frontend/` на GitHub Pages;
- workflow `ci.yml` — поднимает PostgreSQL и гоняет pytest;
- `README.md`, `docs/DEPLOY.md`, `docs/schema.sql`.

---

## 3. Полная цепочка на примере «Аня заходит на сайт»

Ниже — один сквозной сценарий. В скобках — что происходит на каждом слое.

### Шаг 0. Что уже развёрнуто

- Фронтенд: `https://rikkahatsune.github.io/cookiekub/`
- API: `https://cookiekub.vercel.app`
- БД: PostgreSQL в Supabase, 11 таблиц, 12 товаров, 3 кафе, 4 промокода.

### Шаг 1. Аня открывает сайт

1. Браузер: `GET https://rikkahatsune.github.io/cookiekub/`.
2. GitHub Pages отдаёт `index.html`, `css/style.css`, `js/*.js`, SVG-печеньки и шрифты.
3. JS читает `localStorage`:
   - есть ли `cookiekub.token`;
   - есть ли `cookiekub.cart.v1`.
4. JS вызывает `GET https://cookiekub.vercel.app/api/products`.

Что летит:

```http
GET /api/products HTTP/1.1
Host: cookiekub.vercel.app
Origin: https://rikkahatsune.github.io
```

Что делает API:

```sql
SELECT * FROM products
WHERE is_active = TRUE
ORDER BY sort_order, id;
```

Что возвращается:

```json
{
  "products": [
    {
      "id": 1,
      "slug": "klassicheskiy-kubik",
      "name": "Классический кубик",
      "price_cents": 14900,
      "stock_qty": 80,
      "category": "classic"
    }
  ]
}
```

Браузер рисует 12 карточек. На этом этапе в БД ничего не записывается.

### Шаг 2. Аня добавляет печеньки в корзину

Это **полностью клиентское** действие:

```js
localStorage["cookiekub.cart.v1"] = [
  { "product_id": 1, "quantity": 1 },
  { "product_id": 2, "quantity": 1 }
];
```

Никакого запроса на сервер нет. Поэтому корзина переживает перезагрузку страницы, но не синхронизируется между устройствами.

Когда Аня вводит промокод, летит:

```http
POST /api/promos/validate
Content-Type: application/json

{ "code": "COOKIE10", "subtotal_cents": 33800 }
```

API ищет промокод, проверяет активность, даты, лимит и минимальную сумму, считает скидку и возвращает её. Но **итоговая цена всё равно пересчитывается на сервере при создании заказа** — клиенту доверять нельзя.

### Шаг 3. Аня регистрируется

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "anya@example.com",
  "password": "……",
  "full_name": "Аня",
  "privacy_consent": true
}
```

Что происходит в API:

1. Проверка полей: email, пароль 8–128 символов, имя, согласие.
2. Проверка, что email ещё не занят (`lower(email)`).
3. `hash_password(password)` — scrypt с солью. В БД попадает только хеш.
4. `INSERT INTO users (...)`.
5. `issue_session()`:
   - генерируется 32 случайных байта (`secrets.token_urlsafe(32)`);
   - в БД в `sessions.token_hash` кладётся `sha256(token)`, а не сам токен;
   - срок — 7 дней.
6. API возвращает `201`:

```json
{
  "token": "…",
  "expires_at": "2026-11-25T…",
  "user": { "id": 3, "email": "anya@example.com", "role": "user" }
}
```

7. Браузер сохраняет `token` в `localStorage["cookiekub.token"]`.

С этого момента каждый защищённый запрос несёт:

```http
Authorization: Bearer <token>
```

API ищет `sha256(token)` в `sessions`, проверяет `expires_at > now()` и `users.is_active = TRUE`. Если сессии нет или она истекла — `401`.

### Шаг 4. Аня оформляет заказ

```http
POST /api/orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "items": [
    { "product_id": 1, "quantity": 1 },
    { "product_id": 2, "quantity": 1 }
  ],
  "fulfillment": "pickup",
  "cafe_id": 1,
  "promo_code": "COOKIE10",
  "customer_name": "Аня",
  "customer_phone": "+7 900 000-00-00",
  "customer_comment": "побольше шоколада",
  "payment": { "last4": "3456" }
}
```

Важно: полный номер карты, срок и CVV **не отправляются** и не сохраняются. Сервер принимает только 4 цифры для отображения и факт оплаты.

Внутри одного `conn.transaction()`:

1. `SELECT ... FROM products WHERE id = ANY(...) FOR UPDATE` — блокирует строки товаров.
2. Проверяет, что товар активен и остатка хватает.
3. Считает `subtotal` по ценам **из БД**, а не из запроса.
4. `SELECT ... FROM promos ... FOR UPDATE`, проверяет промокод и считает `discount`.
5. `total = subtotal - discount`.
6. Берёт следующий номер из `order_number_seq` → `CK-20261118-0001`.
7. `payment_ref = PAY-…` — платёжная ссылка (в демо платёж не проводится).
8. `INSERT INTO orders (... status='processing', paid_at=now(), card_last4='3456')`.
9. Для каждой позиции — `INSERT INTO order_items` (название и цена фиксируются на момент покупки).
10. `UPDATE products SET stock_qty = stock_qty - quantity`.
11. Если был промокод:
    - `INSERT INTO promo_redemptions (promo_id, order_id, user_id)`;
    - `UPDATE promos SET used_count = used_count + 1`.
12. `COMMIT`.

Ответ:

```json
{
  "order": {
    "id": 1,
    "number": "CK-20261118-0001",
    "status": "processing",
    "status_label": "В обработке",
    "total_cents": 44730,
    "payment": { "last4": "3456", "reference": "PAY-…", "simulated": true }
  }
}
```

Браузер очищает корзину и переходит на `order.html?number=CK-20261118-0001&new=1`.

Если остатка не хватило — `409`, транзакция откатывается, остатки не меняются.

### Шаг 5. Аня смотрит страницу заказа

```http
GET /api/orders/CK-20261118-0001
Authorization: Bearer <token>
```

Для гостя — `POST /api/orders/lookup` с номером и email. Для пользователя API проверяет, что заказ принадлежит ему (или что он админ).

Внутри `GET` вызывается `maybe_complete_orders()`:

```sql
UPDATE orders
SET status = 'completed', completed_at = now()
WHERE status = 'processing'
  AND paid_at IS NOT NULL
  AND paid_at + make_interval(secs => 60) <= now();
```

То есть заказ завершается **лениво**: не отдельным cron-процессом, а при следующем чтении заказа/списка заказов, если прошло 60 секунд. Поэтому в демо не нужен планировщик.

Страница обновляется каждые 5 секунд, пока статус `processing`. Когда приходит `completed`, таймер и кнопка «Обновить» скрываются, показывается «Заказ готов!».

Статусы:

| Статус | Что видит пользователь |
|---|---|
| `processing` | «Печеньки уже в печи», таймер до готовности |
| `completed` | «Заказ готов!», для доставки — «Курьер передал заказ» |
| `cancelled` | «Заказ отменён», остатки и промокод возвращены |

Админ может завершить или отменить заказ раньше:

```http
PATCH /api/admin/orders/1/status
Authorization: Bearer <admin-token>

{ "status": "completed" }
```

При отмене API возвращает `stock_qty` и уменьшает `used_count` промокода.

### Шаг 6. Аня удаляет аккаунт

```http
DELETE /api/auth/account
Authorization: Bearer <token>
Content-Type: application/json

{ "password": "……" }
```

API:

1. Проверяет текущий пароль через scrypt.
2. Вызывает `anonymize_user()`:
   - `users.email` → `deleted+<id>@kubanoid.invalid`;
   - имя → «Удалённый пользователь»;
   - пароль → случайный новый хеш;
   - `is_active = FALSE`, `anonymized_at = now()`;
   - в заказах этого пользователя заменяются имя, email, телефон, комментарий; адрес доставки → «Адрес удалён»;
   - в тикетах email → удалённый, сообщение и ответ обнуляются;
   - `DELETE FROM sessions WHERE user_id = ...`.
3. Возвращает `200 { "ok": true, "deleted": true }`.
4. Браузер удаляет `cookiekub.token` и `cookiekub.cart.v1`, переходит на главную.

Заказы **не удаляются физически**: они остаются для истории, но без персональных данных. Это и есть «право на удаление» в учебной реализации.

---

## 4. Сводная таблица запросов

| Действие | Метод и путь | Авторизация | Что читает/пишет в БД |
|---|---|---|---|
| Открыть сайт | `GET /` (Pages) | нет | ничего |
| Каталог | `GET /api/products` | нет | `products` |
| Карточка товара | `GET /api/products/<slug>` | нет | `products` |
| Кафе | `GET /api/cafes` | нет | `cafes` |
| Проверить промокод | `POST /api/promos/validate` | нет | `promos` |
| Регистрация | `POST /api/auth/register` | нет | `users`, `sessions` |
| Вход | `POST /api/auth/login` | нет | `users`, `sessions` |
| Выход | `POST /api/auth/logout` | Bearer | `sessions` |
| Профиль | `GET /api/auth/me` | Bearer | `users`, `sessions` |
| Сменить пароль | `POST /api/auth/change-password` | Bearer | `users`, `sessions` |
| Создать заказ | `POST /api/orders` | Bearer или гость | `orders`, `order_items`, `products`, `promos`, `promo_redemptions` |
| Мои заказы | `GET /api/orders` | Bearer | `orders`, `order_items` |
| Заказ по номеру | `GET /api/orders/<number>` | Bearer или lookup | `orders`, `order_items`, `cafes` |
| Поиск гостевого заказа | `POST /api/orders/lookup` | нет | `orders` |
| Создать тикет | `POST /api/tickets` | нет | `tickets` |
| Мои тикеты | `GET /api/tickets/my` | Bearer | `tickets` |
| Удалить аккаунт | `DELETE /api/auth/account` | Bearer + пароль | `users`, `orders`, `tickets`, `sessions` |
| Админ: статистика | `GET /api/admin/stats` | Bearer admin | несколько таблиц |
| Админ: товары | `/api/admin/products` | Bearer admin | `products` |
| Админ: заказы | `/api/admin/orders` | Bearer admin | `orders`, `products`, `promos` |
| Админ: пользователи | `/api/admin/users` | Bearer admin | `users`, `sessions` |
| Админ: промокоды | `/api/admin/promos` | Bearer admin | `promos` |
| Админ: тикеты | `/api/admin/tickets` | Bearer admin | `tickets` |
| Админ: аудит | `GET /api/admin/audit` | Bearer admin | `admin_audit` |

---

## 5. Авторизация: что именно проверяется

### Пароль

- Хранится только scrypt-хеш с солью.
- При входе API считает хеш от введённого пароля и сравнивает.
- При смене пароля все сессии пользователя удаляются — старые токены перестают работать.
- При блокировке пользователя (`is_active = false`) все его сессии тоже удаляются.

### Токен сессии

- Генерируется случайно, 32 байта.
- В БД лежит только `sha256(token)`.
- Живёт 7 дней.
- Передаётся в `Authorization: Bearer`.
- При выходе, смене пароля, блокировке и удалении аккаунта удаляется.

### CORS

Браузер с GitHub Pages (`https://rikkahatsune.github.io`) обращается к другому домену (`https://cookiekub.vercel.app`). Поэтому Flask включает CORS только для `/api/*` и только для origin из `CORS_ORIGINS`.

Если открыть API с чужого сайта, браузер не даст прочитать ответ. Это не «пароль», а политика браузера, но она важна для продакшена.

### Rate limit

В памяти процесса (на Vercel — на время жизни инстанса) есть лимиты:

- вход — 5 попыток / 15 минут на email;
- регистрация — 10 / час;
- промокод — 30 / минуту;
- создание заказа — 10 / минуту;
- lookup — 15 / минуту;
- тикет — 5 / час.

Это учебная защита от перебора; для реального продакшена лучше Redis/Upstash.

---

## 6. Почему заказ становится «Выполнен» сам

Планировщика нет. В `orders.py` есть функция `maybe_complete_orders(conn)`:

```sql
UPDATE orders
SET status = 'completed', completed_at = now()
WHERE status = 'processing'
  AND paid_at IS NOT NULL
  AND paid_at + make_interval(secs => :delay) <= now();
```

Она вызывается при:

- `GET /api/orders` (мои заказы);
- `GET /api/orders/<number>` (страница заказа);
- `POST /api/orders/lookup` (гостевой поиск).

Пока пользователь не откроет страницу, заказ может оставаться `processing` дольше 60 секунд. Это нормально для симулятора: статус вычисляется при чтении.

---

## 7. Админка

Админка — отдельная страница `admin.html`, без Django Admin и готовых CMS. Доступ только у `users.role = 'admin'`.

Что можно делать:

- смотреть статистику: пользователи, товары, заказы, выручка, открытые тикеты;
- CRUD товаров; удаление — это архив (`is_active = false`), а не физическое удаление;
- смотреть заказы, завершать и отменять их;
- управлять пользователями: менять роль, блокировать, анонимизировать;
- создавать и архивировать промокоды;
- отвечать на тикеты;
- смотреть журнал `admin_audit`.

Защита от ошибок:

- нельзя снять роль с себя;
- нельзя остаться без последнего админа;
- блокировка пользователя удаляет его сессии.

---

## 8. Что происходит при деплое

### GitHub Pages

Workflow `.github/workflows/pages.yml`:

1. берёт папку `frontend/`;
2. загружает её как artifact;
3. публикует на GitHub Pages.

Сайт: `https://rikkahatsune.github.io/cookiekub/`.

### Vercel

`vercel.json` направляет все запросы в `api/index.py`. Внутри Flask:

- `/api/*` — API;
- остальные пути — статика из `frontend/` (удобно для локальной проверки и для случая, когда Vercel отдаёт всё сам).

`api/index.py` — WSGI-entry, `backend/wsgi.py` — обычная точка входа для gunicorn/локального запуска.

Vercel-проект **cookiekub** берёт переменные окружения из настроек проекта. При каждом push в `main` Vercel пересобирает деплой.

### Supabase

База уже создана. Миграции лежат в `db/migrations/`. Для локальной разработки используется portable PostgreSQL на `127.0.0.1:5433`; для продакшена — Supabase Session pooler с `sslmode=require`.

Особенность Supabase pooler: он может разрывать соединение после нескольких DDL-запросов. Поэтому миграции/seed применялись по одному statement на отдельное соединение. В коде подключения выставлены `connect_timeout=15` и `prepare_threshold=None`.

---

## 9. Локальный запуск (кратко)

```bash
# 1. PostgreSQL на 127.0.0.1:5433, база cookiekub
# 2. миграции и seed
.venv/Scripts/python.exe -m backend.db.migrate
.venv/Scripts/python.exe -m backend.db.seed

# 3. Flask
.venv/Scripts/python.exe -m flask --app backend.app run --host 127.0.0.1 --port 5000
```

Открыть `http://127.0.0.1:5000/`.

Тесты:

```bash
.venv/Scripts/python.exe -m pytest -q
```

---

## 10. Частые вопросы

**Это настоящие заказы и оплата?**
Нет. `payment_ref` начинается с `PAY-`, карта не проверяется, деньги не списываются. Публичный интерфейс оформлен как обычная пекарня; о демо-режиме говорит только одна строка в политике конфиденциальности.

**Где хранится корзина?**
В `localStorage` браузера. На сервер она попадает только при создании заказа.

**Почему после очистки браузера пропала корзина?**
Потому что она не в БД. Это ожидаемо.

**Почему гость может заказать без регистрации?**
Так задумано: гость указывает имя, телефон и email, а заказ хранится с `user_id = NULL`. Посмотреть заказ можно по номеру + email.

**Что будет, если два человека одновременно купят последнюю печеньку?**
Строки товаров блокируются `FOR UPDATE` в транзакции. Второй запрос увидит остаток 0 и получит `409`, остатки не изменятся.

**Можно ли подделать цену в запросе?**
Нет. Сервер берёт цену из `products`, а не из тела запроса. Промокод тоже пересчитывается на сервере.

**Где пароль от базы?**
В `DATABASE_URL` на Vercel и в локальном `.env`; в git его нет. Полный паспорт с значениями — в `CookieKub_ПОЛНАЯ_ИНФОРМАЦИЯ.md`.

**Используются ли cookie?**
Нет. Авторизация — только `localStorage` + `Authorization: Bearer`. Поэтому нет CSRF-cookie-атаки в классическом виде, но есть риск XSS: если злоумышленник выполнит свой JS на странице, он сможет прочитать токен. Поэтому в проекте есть CSP, экранирование и отказ от `innerHTML` с пользовательскими данными.

**Почему на Vercel и GitHub Pages два разных домена?**
Так дешевле и проще: Pages бесплатно отдаёт статику, Vercel бесплатно запускает Flask-функцию. CORS разрешает только домен Pages и сам Vercel.

---

## 11. Куда смотреть в коде

| Что | Файл |
|---|---|
| Создание Flask, CORS, статика | `backend/app.py` |
| Вход/регистрация/удаление | `backend/auth.py` |
| Пароли, токены, сессии, rate limit | `backend/security.py` |
| Заказы, транзакция, автозавершение | `backend/orders.py` |
| Товары, кафе, промокоды | `backend/catalog.py` |
| Админка | `backend/admin.py` |
| Анонимизация | `backend/accounts.py` |
| Схема БД | `db/migrations/001_init.sql` |
| Индексы | `db/migrations/002_indexes.sql` |
| API-клиент фронтенда | `frontend/js/api.js` |
| Корзина и layout | `frontend/js/common.js` |
| Страница заказа | `frontend/js/order.js` |
| Диаграмма пути | `docs/architecture/cookiekub-user-journey.html` |

---

## 12. Главная мысль

CookieKub — это **тонкий статический фронтенд + Flask API + одна PostgreSQL-база**. Браузер хранит только корзину и токен; всё остальное — в Supabase. Пароли — scrypt-хеши, токены — случайные строки, в БД только их sha256. Cookie не используются. Заказ создаётся в транзакции с блокировкой остатков, а завершается лениво через 60 секунд при чтении. Удаление аккаунта не стирает заказы физически, а анонимизирует PII и удаляет сессии.
