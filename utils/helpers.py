# utils/helpers.py
import uuid
import secrets
import logging
import hmac
import random
import secrets
import uuid
import json
from datetime import datetime, timedelta
from aiogram import Bot
from pathlib import Path

from config import settings
import database.db_manager as db
from services.x3ui_service import X3UiClient

logger = logging.getLogger("helpers")

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TARIFFS_PATH = BASE_DIR / "tariffs.json"

def load_tariffs(filepath: str = DEFAULT_TARIFFS_PATH) -> dict:
    """Загружает тарифы из JSON файла в runtime."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

async def grant_vpn_access(user_id: int, days: int = 0, hours: int = 0, minutes: int = 0, total_gb: int = settings.TOTAL_GB_LIMIT) -> str:
    """Выдача доступа на N дней и M минут."""
    user = await db.get_user(user_id)
    client_uuid = user['client_uuid'] if (user and user['client_uuid']) else str(uuid.uuid4())
    sub_id = user['sub_id'] if (user and user['sub_id']) else secrets.token_hex(8)
    client_email = f"tg_{user_id}"
    
    current_expiry = None
    if user and user['expires_at'] and user['status'] == 'active':
        try:
            current_expiry = datetime.fromisoformat(user['expires_at'])
        except ValueError:
            pass
            
    base_time = current_expiry if (current_expiry and current_expiry > datetime.now()) else datetime.now()
    expiry_dt = base_time + timedelta(days=days, hours=hours, minutes=minutes) # Расчет даты
    expiry_ms = int(expiry_dt.timestamp() * 1000)
    
    xui = X3UiClient()
        
    success = await xui.add_client(
        inbound_id=settings.XUI_INBOUND_IDS,
        email=client_email,
        client_uuid=client_uuid,
        sub_id=sub_id,
        tg_id=user_id,
        expiry_time_ms=expiry_ms,
        total_gb_limit=total_gb
    )
    
    if not success:
        activated = await xui.update_client_status(
            inbound_id=settings.XUI_INBOUND_IDS,
            client_uuid=client_uuid,
            email=client_email,
            sub_id=sub_id,
            tg_id=user_id,
            enable=True,
            expiry_time_ms=expiry_ms,
            total_gb_limit=total_gb
        )
        if not activated:
            raise Exception("3X-UI панели отклонила обновление параметров клиента.")
            
    # Запись в локальную базу данных
    await db.activate_user_subscription(user_id, client_uuid, sub_id, days=days, hours=hours, minutes=minutes)
    return f"{settings.XUI_SUB_BASE_URL.rstrip('/')}/buff-subscribe/{sub_id}"

async def process_successful_payment(order_id: str, bot: Bot) -> bool:
    """Единая функция зачисления успешного платежа для вебхуков и ручных проверок."""
    payment_row = await db.get_payment(order_id)
    if not payment_row:
        logger.error(f"Платеж с заказом {order_id} отсутствует в нашей БД!")
        return False

    payment = dict(payment_row)
    if payment['status'] == 'success':
        logger.info(f"Платеж {order_id} уже был ранее обработан.")
        return True

    user_id = payment['user_id']
    amount = payment['amount']
    tariff_id = payment.get('tariff_id')

    tariffs = load_tariffs()

    tariff = None
    if tariff_id and tariff_id in tariffs:
        tariff = tariffs[tariff_id]
    else:
        # Резервный сопоставитель тарифа по цене
        tariff = next((t for t in tariffs.values() if abs(t['price'] - amount) < 1.0), None)

    if tariff:
        days = tariff.get("days", 0)
        minutes = tariff.get("minutes", 0)
        total_gb = tariff.get("total_gb", settings.TOTAL_GB_LIMIT)
        tariff_label = tariff.get("name", "VPN Подписка")
    else:
        days, minutes, total_gb, tariff_label = 30, 0, settings.TOTAL_GB_LIMIT, "Стандартный (30 дней)"

    logger.info(f"Начисление подписки за заказ {order_id}. User: {user_id}, Тариф: '{tariff_label}', Дней: {days}")

    await db.mark_payment_success(order_id)
    sub_link = await grant_vpn_access(user_id, days=days, minutes=minutes, total_gb=total_gb)

    try:
        await bot.send_message(
            user_id,
            f"🎉 **Оплата зачислена!**\n\n"
            f"📅 Активирован тариф **'{tariff_label}'**.\n"
            f"🔗 Ссылка на подписку:\n`{sub_link}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

    return True

async def activate_trial_period(user_id: int, bot: Bot) -> tuple[bool, str]:
    """Логика активации 1-дневного триала по запросу c бота."""
    user = await db.create_or_get_user(user_id)
    
    if user['trial_used'] == 1:
        return False, "Вы уже использовали ваш пробный период ранее."
        
    client_uuid = user['client_uuid'] if (user and user['client_uuid']) else str(uuid.uuid4())
    sub_id = user['sub_id'] if (user and user['sub_id']) else secrets.token_hex(8)
    client_email = f"tg_{user_id}"
    
    # Ровно 1 день
    expiry_dt = datetime.now() + timedelta(days=1)
    expiry_ms = int(expiry_dt.timestamp() * 1000)
    
    xui = X3UiClient()
        
    success = await xui.add_client(
        inbound_id=settings.XUI_INBOUND_IDS,
        email=client_email,
        client_uuid=client_uuid,
        sub_id=sub_id,
        tg_id=user_id,
        expiry_time_ms=expiry_ms,
        total_gb_limit=10
    )
    
    if not success:
        activated = await xui.update_client_status(
            inbound_id=settings.XUI_INBOUND_IDS,
            client_uuid=client_uuid,
            email=client_email,
            sub_id=sub_id,
            enable=True,
            tg_id=user_id,
            expiry_time_ms=expiry_ms,
            total_gb_limit=10
        )
        if not activated:
            return False, "Панель отклонила активацию тестового периода."
            
    # Сохраняем использование триала
    await db.use_trial_db(user_id, client_uuid, sub_id, expiry_dt.isoformat())
    
    # Отправляем сообщение пользователю в TG
    sub_link = f"{settings.XUI_SUB_BASE_URL.rstrip('/')}/buff-subscribe/{sub_id}"
    try:
        await bot.send_message(
            user_id,
            "🎁 **Вам активирован бесплатный пробный период на 1 день!**\n\n"
            f"🔗 Ссылка на вашу подписку:\n`{sub_link}`\n\n"
            "Инструкции по настройке доступны в меню бота /start.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить TG-сообщение о триале: {e}")
        
    return True, sub_link

async def create_temp_user(bot: Bot) -> tuple[bool, str]:
    # Генерируем уникальный временный sub_id с префиксом temp_
    sub_id = f"temp_{secrets.token_hex(6)}"
    client_uuid = str(uuid.uuid4())
    client_email = sub_id

    # Создаем временный отрицательный ID пользователя для SQLite
    fake_user_id = -random.randint(100000000, 999999999)

    # 30 минут действия демо-периода
    expiry_dt = datetime.now() + timedelta(minutes=30)
    expiry_ms = int(expiry_dt.timestamp() * 1000)

    xui = X3UiClient()
    
    success = await xui.add_client(
        inbound_id=settings.XUI_INBOUND_IDS,
        email=client_email,
        client_uuid=client_uuid,
        sub_id=sub_id,
        tg_id=fake_user_id,
        expiry_time_ms=expiry_ms,
        total_gb_limit=1
    )
    
    if not success:
        return False, "Панель отклонила активацию демо-пользователя"
            
    # Сохраняем использование триала
    await db.create_or_get_user(fake_user_id, sub_id, expires_at=expiry_dt)

    sub_link = f"{settings.XUI_SUB_BASE_URL.rstrip('/')}/buff-subscribe/{sub_id}"
        
    return True, sub_link

def verify_internal_token(client_secret: str) -> bool:
    """
    Проверяет секретный токен из заголовка 'X-Internal-Secret'
    Возвращает True, если токен совпадает, иначе False.
    """    
    if not client_secret:
        return False
        
    # 2. Безопасная сверка токенов (защита от Timing Attacks)
    return hmac.compare_digest(client_secret, settings.INTERNAL_API_SECRET)