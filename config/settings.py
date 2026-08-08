# Все настройки и FeatureToggle
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", 0))
WEB_PORT = int(os.getenv("WEB_PORT", 8000))
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "")

# FEATURE TOGGLE
PAYMENT_ENABLED = os.getenv("PAYMENT_ENABLED", "False").lower() in ("true", "1", "yes")

# Тарифная сетка
PRICE_TEST_TARIFF = float(os.getenv("PRICE_TEST_TARIFF", 12.00))
PRICE_30_DAYS = float(os.getenv("PRICE_30_DAYS", 300.00))
PRICE_90_DAYS = float(os.getenv("PRICE_90_DAYS", 800.00))

# --- ПАРАМЕТРЫ ПЛАТЕЖЕЙ (заполняются при PAYMENT_ENABLED=True) ---
PAYMENT_URL = os.getenv("PAYMENT_URL", "")
PAYMENT_SHOP_ID = os.getenv("PAYMENT_SHOP_ID", "")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY", "")
PAYMENT_CALLBACK_KEY = os.getenv("PAYMENT_CALLBACK_KEY", "")
PAYMENT_WEBHOOK_URL = os.getenv("PAYMENT_WEBHOOK_URL", "")

# --- НАСТРОЙКИ 3X-UI ---
XUI_URL = os.getenv("XUI_URL", "http://127.0.0.1:2053")
XUI_TOKEN = os.getenv("XUI_TOKEN", "1234")

raw_inbound_ids = os.getenv("XUI_INBOUND_IDS", "1")
XUI_INBOUND_IDS = [
    int(x.strip()) for x in raw_inbound_ids.split(",") if x.strip()
]
XUI_SUB_BASE_URL = os.getenv("XUI_SUB_BASE_URL", "http://127.0.0.1:2053")

# Лимиты для клиентов
LIMIT_IP = int(os.getenv("LIMIT_IP", 2))
TOTAL_GB_LIMIT = int(os.getenv("TOTAL_GB_LIMIT", 100))