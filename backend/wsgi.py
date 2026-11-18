"""WSGI entrypoint для Render/Gunicorn/Alwaysdata."""
import sys
from pathlib import Path

# Alwaysdata/uWSGI загружает файл как top-level модуль: добавляем корень проекта,
# чтобы работал пакетный импорт backend.*
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:  # запуск как пакет: python -m backend.wsgi
    from .app import create_app
except ImportError:  # gunicorn/alwaysdata: backend.wsgi:application
    from backend.app import create_app

app = create_app()
# Alwaysdata/WSGI ищет именно application.
application = app
