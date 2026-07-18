# utils/helpers.py
import uuid
import secrets
import logging
from datetime import datetime, timedelta
from aiogram import Bot

from config import settings
import database.db_manager as db
from services.x3ui_service import X3UiClient

logger = logging.getLogger("helpers")

async def grant_vpn_access(user_id: int, days: int) -> str:
    """Обобщенная функция выдачи/продления доступа на N дней."""
    user = await db.get_user(user_id)
    client_uuid = user['client_uuid'] if (user and user['client_uuid']) else str(uuid.uuid4())
    sub_id = user['sub_id'] if (user and user['sub_id']) else secrets.token_hex(8)
    client_email = f"tg_{user_id}"
    
    # 1. Считаем дату окончания на основе переданных дней
    # Если у пользователя уже активна подписка, продлеваем с даты окончания
    current_expiry = None
    if user and user['expires_at'] and user['status'] == 'active':
        try:
            current_expiry = datetime.fromisoformat(user['expires_at'])
        except ValueError:
            pass
            
    base_time = current_expiry if (current_expiry and current_expiry > datetime.now()) else datetime.now()
    expiry_dt = base_time + timedelta(days=days)
    expiry_ms = int(expiry_dt.timestamp() * 1000)
    
    xui = X3UiClient()
        
    # 2. Добавляем в панель
    success = await xui.add_client(
        inbound_id=settings.XUI_INBOUND_ID,
        email=client_email,
        client_uuid=client_uuid,
        sub_id=sub_id,
        tg_id=user_id,
        expiry_time_ms=expiry_ms
    )
    
    # 3. Если уже был — обновляем статус и продлеваем время
    if not success:
        activated = await xui.update_client_status(
            inbound_id=settings.XUI_INBOUND_ID,
            client_uuid=client_uuid,
            email=client_email,
            sub_id=sub_id,
            enable=True,
            tg_id=user_id,
            expiry_time_ms=expiry_ms
        )
        if not activated:
            raise Exception("3X-UI отклонила обновление параметров клиента.")
            
    # 4. Фиксируем в локальной БД
    await db.activate_user_subscription(user_id, client_uuid, sub_id, days=days)
    return f"{settings.XUI_SUB_BASE_URL.rstrip('/')}/sub/{sub_id}"

async def activate_trial_period(user_id: int, bot: Bot) -> tuple[bool, str]:
    """Логика активации 1-дневного триала по запросу с сайта или бота."""
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
        inbound_id=settings.XUI_INBOUND_ID,
        email=client_email,
        client_uuid=client_uuid,
        sub_id=sub_id,
        tg_id=user_id,
        expiry_time_ms=expiry_ms
    )
    
    if not success:
        activated = await xui.update_client_status(
            inbound_id=settings.XUI_INBOUND_ID,
            client_uuid=client_uuid,
            email=client_email,
            sub_id=sub_id,
            enable=True,
            tg_id=user_id,
            expiry_time_ms=expiry_ms
        )
        if not activated:
            return False, "Панель отклонила активацию тестового периода."
            
    # Сохраняем использование триала
    await db.use_trial_db(user_id, client_uuid, sub_id, expiry_dt.isoformat())
    
    # Отправляем сообщение пользователю в TG
    sub_link = f"{settings.XUI_SUB_BASE_URL.rstrip('/')}/sub/{sub_id}"
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