"""WSGI entrypoint для Vercel/Gunicorn."""
import sys
from pathlib import Path

# WSGI-серверы (Gunicorn, Vercel) загружают файл как top-level модуль:
# добавляем корень проекта, чтобы работал пакетный импорт backend.*
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:  # запуск как пакет: python -m backend.wsgi
    from .app import create_app
except ImportError:  # gunicorn/vercel: backend.wsgi:application
    from backend.app import create_app

app = create_app()
# WSGI-серверы ищут именно application.
application = app
