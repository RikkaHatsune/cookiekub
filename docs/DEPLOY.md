# Деплой CookieKub: GitHub Pages + Render + Neon

Это инструкция для варианта **A1**: статический фронтенд на GitHub Pages, Flask-бэкенд на
Render Free, PostgreSQL на Neon Free.

## Почему не всё на GitHub Pages

GitHub Pages — это хостинг статических файлов. Он отдаёт HTML/CSS/JS, но **не запускает Python**,
не держит постоянный процесс и не подключается к PostgreSQL. Поэтому:

- `frontend/` публикуется на GitHub Pages;
- `backend/` работает на Render как обычный Python-процесс;
- база живёт на Neon и доступна по `DATABASE_URL`.

Браузер преподавателя открывает `https://<username>.github.io/<repo>/`, JS-код обращается к
`https://<render-service>.onrender.com/api/...`. Это обычный CORS-запрос, разрешённый в
`CORS_ORIGINS`.

## 0. Что понадобится

- Аккаунт GitHub.
- Аккаунт Render (можно войти через GitHub).
- Аккаунт Neon (можно войти через GitHub).
- Git на компьютере (в проекте уже есть `git` 2.56).

## 1. GitHub: репозиторий и токен

### Вариант «через браузер»

1. Войдите в GitHub в Yandex Browser.
2. Создайте новый **public** репозиторий, например `cookiekub`, без README и `.gitignore`
   (они уже есть в проекте).
3. В корне проекта выполните:

```bash
git init
git add .
git commit -m "CookieKub: витрина, заказы, KubanoID и админка"
git branch -M main
git remote add origin https://github.com/<username>/cookiekub.git
git push -u origin main
```

При push Git попросит логин/пароль. В качестве пароля GitHub больше не принимает обычный пароль —
нужен **personal access token**.

### Как выпустить токен

1. GitHub → аватар → **Settings** → **Developer settings** → **Personal access tokens** →
   **Tokens (classic)** → **Generate new token (classic)**.
2. Note: `cookiekub-deploy`; Expiration: 7 days (или 30, если удобнее).
3. Отметьте scopes: **`repo`** и **`workflow`** (workflow нужен, чтобы пушить
   `.github/workflows/`).
4. Нажмите **Generate token** и сразу скопируйте `ghp_...` — второй раз он не показывается.
5. Не вставляйте токен в чат и не коммитьте его. Сохраните в файл **вне репозитория**:

```text
F:\CodeProject\.secrets\gh_token.txt
```

Можно использовать его при push:

```bash
git remote set-url origin https://<username>:<TOKEN>@github.com/<username>/cookiekub.git
git push -u origin main
```

Но безопаснее настроить Git Credential Manager и вставить токен в диалоге пароля — тогда токен не
попадёт в `.git/config`.

### Если токен не хочется

Можно настроить SSH-ключ:

```bash
ssh-keygen -t ed25519 -C "cookiekub"
# публичный ключ ~/.ssh/id_ed25519.pub добавить в GitHub → Settings → SSH and GPG keys
git remote set-url origin git@github.com:<username>/cookiekub.git
```

## 2. GitHub Pages

После первого push:

1. Репозиторий → **Settings** → **Pages**.
2. **Build and deployment → Source: GitHub Actions**.
3. workflow `Deploy frontend to GitHub Pages` (`.github/workflows/pages.yml`) сам вызовет
   `actions/configure-pages` с `enablement: true`, соберёт `frontend/` и опубликует.
4. Дождитесь зелёной галочки в **Actions** и откройте
   `https://<username>.github.io/cookiekub/`.

Если Pages не включился автоматически, выполните шаг 2 вручную и перезапустите workflow
(**Actions → Deploy frontend to GitHub Pages → Re-run all jobs**).

## 3. Neon: PostgreSQL

1. <https://neon.tech> → **New Project** → регион ближе к Render (например, Frankfurt).
2. В **Connection string** выберите **Pooled connection** и скопируйте строку вида:

```text
postgresql://<user>:<password>@<host>-pooler.<region>.aws.neon.tech/<db>?sslmode=require
```

3. Проверьте, что в конце есть `sslmode=require`. Без SSL Neon не подключится.
4. Ничего вручную создавать не нужно: при старте Render выполнит
   `python -m db.migrate && python -m db.seed`.

> Бесплатный Neon: 1 ГБ storage, проект засыпает при простое. Первый запрос после паузы может быть
> медленнее. Данные не удаляются, в отличие от бесплатного Render PostgreSQL (его не используем).

## 4. Render: Flask API

1. <https://render.com> → **New** → **Blueprint** (или **Web Service**).
2. Подключите GitHub-репозиторий. Render увидит `render.yaml`.
3. Если создаёте вручную:
   - Runtime: **Python 3**;
   - Root Directory: оставьте пустым (корень репозитория);
   - Build Command: `pip install -r backend/requirements.txt`;
   - Start Command:
     `python -m backend.db.migrate && python -m backend.db.seed && gunicorn backend.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`;
   - Plan: **Free**;
   - Health Check Path: `/api/health`.
4. Environment variables:

| Переменная | Значение |
|---|---|
| `DATABASE_URL` | pooled-строка Neon с `sslmode=require` |
| `SECRET_KEY` | длинная случайная строка (Render может сгенерировать) |
| `MAINTENANCE_TOKEN` | случайная строка для purge-workflow |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | `https://<username>.github.io` |
| `SUPPORT_EMAIL` | `support@cookiekub.ru` |
| `ORDER_COMPLETE_DELAY_SECONDS` | `60` |
| `SESSION_TTL_DAYS` | `7` |

5. Нажмите **Deploy**. В логах должно быть:
   - `+ 001_init.sql`, `+ 002_indexes.sql`;
   - `Seed применён: 12 товаров, 3 кафе, 4 промокода, 2 аккаунта...`;
   - `Listening at: http://0.0.0.0:...`.
6. Проверьте `https://<service>.onrender.com/api/health` — должен вернуть
   `{"status":"ok","db":true,...}`.

### Если URL Render отличается

В `frontend/js/config.js`:

```js
apiBase: location.hostname.endsWith("github.io")
  ? "https://cookiekub-api.onrender.com"
  : ""
```

Замените на фактический URL. После коммита Pages пересоберётся автоматически. Временно можно
проверить без правки файла:

```js
localStorage.setItem("cookiekub.apiBase", "https://ваш-сервис.onrender.com");
location.reload();
```

## 5. Проверка после деплоя

1. Откройте Pages-URL. В шапке должны быть «Главная / Каталог / Поддержка».
2. Каталог: 12 карточек, ровно 5 в ряд на широком экране.
3. Добавьте 3 печеньки, введите `COOKIE10` — итог уменьшится на 10%.
4. Оформите заказ гостем: любой номер карты, любой CVV, email. Должны появиться зелёная плашка,
   номер `CK-...`, кафе и карта.
5. Войдите как `admin@cookiekub.ru / Admin123!`, откройте `/admin.html`, завершите заказ.
   Обновите страницу заказа — статус «Выполнен».
6. Войдите как `user@cookiekub.ru / User123!` — в кабинете виден заказ.
7. Проверьте 403: гость открывает `/admin.html` — видит текст
   «Лучше закажите печеньку, а здесь - мы лучше сами» и форму входа KubanoID.

## 6. Частые проблемы

**`db:false` в health.** Неверный `DATABASE_URL`, нет `sslmode=require`, или Neon спит.
Проверьте строку и логи Render.

**CORS-ошибка в браузере.** В `CORS_ORIGINS` должен быть точный origin Pages:
`https://<username>.github.io` (без `/cookiekub/`). Для локальной проверки добавьте
`http://127.0.0.1:5000`.

**На Pages белый экран / 404 на внутренних ссылках.** Проверьте, что Pages Source =
GitHub Actions, а не «Deploy from a branch». Все ссылки в проекте относительные.

**Render засыпает.** Это бесплатный тариф. `keepalive.yml` пингует health каждые 10 минут, но
GitHub Actions может задерживать cron. Первый запрос после сна — до ~60 секунд.

**Сбросить демо-данные.** В Render Shell (или локально) выполните
`python -m db.seed`; сид идемпотентен. Полный сброс — только для локальной БД:
`python scripts/reset_db.py`.

**Не пушится workflow.** Токену не хватает scope `workflow`. Перевыпустите classic token с
`repo` + `workflow`.

## 7. Что не хранится и не отправляется

- Полный номер карты, срок и CVV не уходят на сервер: JS отправляет только `last4`.
- Реальные письма не отправляются: тикет сохраняется в БД, текст «письмо отправлено» —
  симуляция.
- Пароли хранятся как scrypt-хэш; токены — как SHA-256.
