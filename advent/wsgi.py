"""
WSGI входна точка (Apache + mod_wsgi).

WSGIScriptAlias / /път/до/проекта/advent/wsgi.py
"""

import os
import sys
from pathlib import Path

# Позволява на mod_wsgi да намери пакета „advent“ без допълнителен python-path.
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from django.core.wsgi import get_wsgi_application  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "advent.settings")

application = get_wsgi_application()
