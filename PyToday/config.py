import os
import secrets
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://PythonToday:JXTg6cIx7tAhOJBk@cluster0.obhmjth.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8447170900:AAHXcUNr7X3ZXbo7sSgg9hu9pLDjn8Gsl-g")

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "a7e5f2d8c9b1a0f3e4d2c8b7a6f5e1d3c9a8b7f6e5d4c3b2a1f0e9d8c7b6a5")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = secrets.token_urlsafe(32)
    print("WARNING: ENCRYPTION_KEY not set. Generated a random key for this session.")
    print("For production, please set ENCRYPTION_KEY environment variable.")

ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "7756391784").split(",") if x.strip()]

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

BOT_USERNAME = os.getenv("BOT_USERNAME", "PyToday Adbot")
ACCOUNT_NAME_SUFFIX = os.getenv("ACCOUNT_NAME_SUFFIX", "- PyToday Ads")
ACCOUNT_BIO_TEMPLATE = os.getenv("ACCOUNT_BIO_TEMPLATE", "Adbot by @dojutso | Bot @PyTodayAdsBot")

START_IMAGE_URL = "https://i.ibb.co/p6mFW8JQ/file-3545.jpg"

ADMIN_ONLY_MODE = os.getenv("ADMIN_ONLY_MODE", "False").lower() == "true"

AUTO_REPLY_ENABLED = os.getenv("AUTO_REPLY_ENABLED", "False").lower() == "true"
AUTO_REPLY_TEXT = os.getenv("AUTO_REPLY_TEXT", "Abhi main offline hu. Tum apna text likhdo main jald se jald reply dene ki koshish karunga.")

AUTO_GROUP_JOIN_ENABLED = os.getenv("AUTO_GROUP_JOIN_ENABLED", "False").lower() == "true"
