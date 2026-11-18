# Деплой CookieKub: GitHub Pages + Vercel + Supabase

Рабочая схема проекта:

| Часть | Где | URL |
|---|---|---|
| Фронтенд | GitHub Pages | <https://rikkahatsune.github.io/cookiekub/> |
| API | Vercel (Python/Flask) | <https://cookiekub.vercel.app> |
| База | Supabase (PostgreSQL) | `*.supabase.co`, Session pooler |
| Код | GitHub | <https://github.com/RikkaHatsune/cookiekub> |

GitHub Pages не запускает Python и не подключается к PostgreSQL, поэтому API и БД живут отдельно.

## 0. Что понадобится

- GitHub-аккаунт и публичный репозиторий.
- Vercel-аккаунт (вход через GitHub).
- Supabase-аккаунт (вход через GitHub).
- Локальный git и Python 3.12.

## 1. GitHub: репозиторий и push

```bash
git add .
git commit -m "CookieKub: ..."
git branch -M main
git remote add origin git@github.com:<username>/cookiekub.git
git push -u origin main
```

В проекте уже настроен SSH-ключ `~/.ssh/cookiekub` и `~/.ssh/config`:

```text
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/cookiekub
```

Порт 443 нужен, если прямой SSH (22) блокируется провайдером.

## 2. GitHub Pages

Workflow уже лежит в `.github/workflows/pages.yml`: он берёт `frontend/` и публикует на Pages.

1. GitHub → репозиторий → **Settings** → **Pages**.
2. **Build and deployment → Source** → **GitHub Actions**.
3. Сделайте push в `main` или запустите workflow вручную (**Actions → Deploy frontend to GitHub Pages → Run workflow**).
4. Через 1–2 минуты сайт будет доступен по адресу:

```text
https://<username>.github.io/cookiekub/
```

Если Pages ещё не включены, первый запуск `actions/configure-pages` может упасть с
`Resource not accessible by integration`. После включения Pages просто перезапустите workflow.

## 3. Supabase: база

1. Создайте проект Supabase (Free): регион Europe, пароль БД сохраните.
2. Откройте **Connect → Direct → Session pooler** и скопируйте строку:

```text
postgresql://postgres.<project-ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require
```

3. Примените миграции и seed **с локальной машины**, передав строку подключения:

```bash
cd cookiekub
export DATABASE_URL='postgresql://...'
.venv/Scripts/python.exe -m backend.db.migrate
.venv/Scripts/python.exe -m backend.db.seed
```

Особенность Session pooler: он может разрывать соединение после нескольких DDL-подряд. Если
`migrate` падает на середине:

- примените оставшиеся statement по одному (psql или отдельные соединения);
- проверьте `schema_migrations` — там должны быть версии `001` и `002`;
- `seed.py` работает с `autocommit=True`.

В коде подключения уже стоят `connect_timeout=15` и `prepare_threshold=None` — это нужно для
пулера.

Проверка:

```sql
SELECT count(*) FROM products;   -- 12
SELECT count(*) FROM cafes;      -- 3
SELECT count(*) FROM promos;     -- 4
```

## 4. Vercel: API

1. Vercel → **Add New → Project** → импортируйте `RikkaHatsune/cookiekub`.
2. Root Directory: `./`.
3. Framework Preset: **Flask** (Vercel сам увидит `api/index.py` и `vercel.json`).
4. Добавьте переменные окружения (Production):

| Ключ | Значение |
|---|---|
| `DATABASE_URL` | строка Supabase Session pooler |
| `SECRET_KEY` | случайная строка |
| `MAINTENANCE_TOKEN` | случайная строка |
| `APP_ENV` | `production` |
| `SUPPORT_EMAIL` | `support@cookiekub.ru` |
| `ORDER_COMPLETE_DELAY_SECONDS` | `60` |
| `SESSION_TTL_DAYS` | `7` |
| `CORS_ORIGINS` | `https://<username>.github.io,https://cookiekub.vercel.app` |
| `RATE_LIMIT_ENABLED` | `true` |

5. Нажмите **Deploy**. После сборки проверьте:

```text
https://cookiekub.vercel.app/api/health
```

Ожидаемый ответ:

```json
{ "status": "ok", "db": true }
```

Если `db: false` — проверьте `DATABASE_URL`, SSL (`sslmode=require`) и что Supabase не на паузе.

### Файлы, которые делают Vercel-деплой

- `api/index.py` — WSGI-entry для serverless-функции;
- `vercel.json` — все маршруты в `api/index.py` (Flask сам отдаёт и `/api/*`, и статику);
- `requirements.txt` в корне — зависимости для Vercel;
- `backend/wsgi.py` — обычная точка входа для локального запуска/gunicorn.

## 5. Связка фронтенда с API

В `frontend/js/config.js`:

```js
apiBase: location.hostname.endsWith("github.io")
  ? "https://cookiekub.vercel.app"
  : ""
```

То есть на GitHub Pages запросы идут на Vercel, а локально — на тот же origin.

`CORS_ORIGINS` на Vercel должен содержать **origin** Pages (без пути):

```text
https://rikkahatsune.github.io
```

## 6. Проверка после деплоя

1. Открыть `https://rikkahatsune.github.io/cookiekub/` — должны загрузиться стили и 12 товаров.
2. Открыть `https://cookiekub.vercel.app/css/style.css` — `200`.
3. Открыть `https://cookiekub.vercel.app/api/health` — `200`, `db: true`.
4. Войти как `admin@cookiekub.ru` / `Admin123!`, проверить админку.
5. Оформить гостевой заказ, применить `COOKIE10`, проверить страницу заказа.
6. Через 60 секунд обновить страницу — статус должен стать «Выполнен».

## 7. Обновление

```bash
git add .
git commit -m "..."
git push
```

- GitHub Pages пересоберётся workflow’ом.
- Vercel пересоберётся автоматически из `main`.

## 8. Ограничения бесплатных тарифов

- Vercel Free: serverless-функции имеют лимит времени и «холодный старт»; первый запрос после
  простоя может быть медленнее.
- Supabase Free: проект может уходить в паузу при простое; есть лимиты storage и connections.
- GitHub Pages: только статика, без серверного кода.

## 9. Если что-то не работает

| Симптом | Причина | Что делать |
|---|---|---|
| Сайт без CSS/JS | Vercel-маршруты отдают только `/api/*` | `vercel.json`: `{"src":"/(.*)","dest":"api/index.py"}` |
| `db: false` | неверный `DATABASE_URL`/SSL | проверить Session pooler и `sslmode=require` |
| CORS-ошибка | origin не в `CORS_ORIGINS` | добавить `https://<username>.github.io` |
| 404 на API | неверный `apiBase` | проверить `frontend/js/config.js` |
| Pages 404 | Pages не включены | Settings → Pages → Source: GitHub Actions |
