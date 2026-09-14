"""Production entry point — gunicorn wsgi:app. See docs/setup/production.md."""

from vulniverse_api import create_app

app = create_app()
