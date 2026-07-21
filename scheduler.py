# scheduler.py
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import settings
import database.db_manager as db
from services.x3ui_service import X3UiClient

logger = logging.getLogger("scheduler")

async def deactivate_expired_subscriptions_job(bot: Bot):
    """Задача 1: Частая проверка (каждые 10 минут) и отключение истёкших подписок."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    xui = X3UiClient()
    
    expired_users = await db.get_expired_users(now_str)
    if not expired_users:
        return

    logger.info(f"Найдено {len(expired_users)} просроченных подписок. Выполняется отключение...")
    
    for user in expired_users:
        user_id = user["user_id"]
        client_uuid = user["client_uuid"]
        sub_id = user["sub_id"]
        
        logger.info(f"Попытка отключить пользователя {user_id} (UUID: {client_uuid})")
        
        # 1. Сначала отключаем в 3X-UI панели
        success = await xui.update_client_status(
            inbound_id=settings.XUI_INBOUND_ID,
            client_uuid=client_uuid,
            email=f"tg_{user_id}",
            sub_id=sub_id,
            enable=False,
            tg_id=user_id,
        )
        
        # 2. Обновляем статус в нашей локальной БД ТОЛЬКО после успеха в 3X-UI
        if success:
            await db.update_user_status(user_id, 'expired')
            logger.info(f"Пользователь {user_id} успешно отключен в панели и БД.")
            
            # 3. Отправляем уведомление
            try:
                await bot.send_message(
                    user_id, 
                    "⚠️ **Срок действия вашей VPN-подписки истёк.**\n\n"
                    "Доступ к серверам приостановлен. Вы можете продлить подписку прямо в меню бота!",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
        else:
            logger.error(f"⚠️ Панель 3X-UI не подтвердила отключение {user_id}. Повторим попытку через 10 минут.")


async def send_expiry_warnings_job(bot: Bot):
    """Задача 2: Отправка предупреждений о скором истечении (1 и 3 дня)."""
    now = datetime.now()
    
    # 1. Предупреждение за 3 дня (72 часа)
    target_3d = (now + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
    users_3d = await db.get_users_for_warning(target_3d, "3d")
    
    for user in users_3d:
        user_id = user["user_id"]
        try:
            await bot.send_message(
                user_id,
                "ℹ️ **Напоминание:** Ваша VPN-подписка истекает через 3 дня.\n"
                "Продлите её заранее, чтобы не потерять доступ!",
                parse_mode="Markdown"
            )
            await db.mark_user_warned(user_id, "3d")
        except Exception as e:
            logger.warning(f"Ошибка отправки 3d предупреждения {user_id}: {e}")

    # 2. Предупреждение за 1 день (24 часа)
    target_1d = (now + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    users_1d = await db.get_users_for_warning(target_1d, "1d")
    
    for user in users_1d:
        user_id = user["user_id"]
        try:
            await bot.send_message(
                user_id,
                "⏳ **Внимание:** Ваша VPN-подписка заканчивается завтра!\n"
                "Рекомендуем продлить её прямо сейчас во избежание отключения.",
                parse_mode="Markdown"
            )
            await db.mark_user_warned(user_id, "1d")
        except Exception as e:
            logger.warning(f"Ошибка отправки 1d предупреждения {user_id}: {e}")


def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    
    # Отключение просроченных ключей каждые 10 минут
    scheduler.add_job(deactivate_expired_subscriptions_job, 'interval', minutes=10, args=[bot])
    
    # Проверка и отправка предупреждений раз в час
    scheduler.add_job(send_expiry_warnings_job, 'interval', hours=1, args=[bot])
    
    scheduler.start()
    logger.info("Фоновый планировщик задач успешно запущен (интервалы: 10 мин / 1 час).")