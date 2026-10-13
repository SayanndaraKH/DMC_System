import os
import sys
from pathlib import Path

# Add project root directory to Python path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dms_project.settings')

# Initialize Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

import serverless_wsgi

def handler(event, context):
    """
    Netlify Functions / AWS Lambda entry point for Django WSGI.
    Handles incoming HTTP requests and routes them to Django.
    """
    return serverless_wsgi.handle_request(application, event, context)
