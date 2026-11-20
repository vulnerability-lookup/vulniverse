"""Production entry point — gunicorn wsgi:app. See https://vulnerability-lookup.github.io/vulniverse/docs/setup/production/"""

from vulniverse_api import create_app

app = create_app()
