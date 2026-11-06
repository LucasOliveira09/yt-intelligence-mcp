import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, mode=0o700)

ACCOUNTS_FILE = DATA_DIR / "accounts.json"
CACHE_DB = DATA_DIR / "cache.sqlite3"
COOKIES_FILE = DATA_DIR / "cookies.txt"

# Quota-safe defaults
DEFAULT_COMPETITOR_LIMIT = 30
DEFAULT_OUTLIER_THRESHOLD = 2.0
MEGA_VIRAL_THRESHOLD = 4.0
