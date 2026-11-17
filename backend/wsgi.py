"""WSGI entrypoint для Render/Gunicorn (rootDir=backend)."""
try:  # запуск как пакет: python -m backend.wsgi
    from .app import create_app
except ImportError:  # gunicorn wsgi:app из каталога backend
    from app import create_app

app = create_app()
