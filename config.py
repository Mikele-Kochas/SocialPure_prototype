import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Flask Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Limits
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "20"))
MAX_ACTOR_RESULTS = int(os.getenv("MAX_ACTOR_RESULTS", "100"))
SCRAPING_TIMEOUT = int(os.getenv("SCRAPING_TIMEOUT", "300"))

# Validate required variables
if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN nie jest ustawiony w zmiennych środowiskowych")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY nie jest ustawiony w zmiennych środowiskowych")
