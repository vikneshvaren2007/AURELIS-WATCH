"""
AURELIS Luxury Watch E-Commerce Platform
Root Application Entry Point for WSGI Servers (Gunicorn / Render / Heroku)
"""

import os
import sys
from pathlib import Path

# Ensure root directory is on python sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Expose Flask application instance for Gunicorn (gunicorn app:app)
from backend.app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
