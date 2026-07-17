# scheduler.py
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from config import settings
import database.db_manager as db
from services.x3ui_service import X3UiClient

logger = logging.getLogger("scheduler")

async def check_subscriptions_job(bot: Bot):
    logger.info("Запуск фоновой проверки подписок...")
    now = datetime.now()
    now_str = now.isoformat()
    xui = X3UiClient()
    
    # 1. Заморозка просроченных клиентов
    expired_users = await db.get_expired_users(now_str)
    if expired_users:
        logger.info(f"Найдено {len(expired_users)} просроченных подписок. Начинаем отключение...")
        
        # Авторизуемся в панели один раз для проведения пакетной деактивации
        for user in expired_users:
            user_id = user["user_id"]
            client_uuid = user["client_uuid"]
            sub_id = user["sub_id"]
            
            logger.info(f"Фоновое отключение пользователя {user_id} (UUID: {client_uuid})")
            
            # Обновляем статус в нашей локальной БД бота
            await db.update_user_status(user_id, 'expired')
            
            # Замораживаем доступ в 3X-UI (это автоматически применится на всех рабочих нодах)
            success = await xui.update_client_status(
                inbound_id=settings.XUI_INBOUND_ID,
                client_uuid=client_uuid,
                email=f"tg_{user_id}",
                sub_id=sub_id,
                enable=False
            )
            
            if success:
                logger.info(f"Пользователь {user_id} успешно отключен в панели 3X-UI.")
            else:
                logger.error(f"Панель 3X-UI отклонила отключение пользователя {user_id}.")
            
            # Отправляем уведомление пользователю в Telegram
            try:
                await bot.send_message(
                    user_id, 
                    "⚠️ Срок действия вашей VPN подписки истёк. Доступ к серверам заблокирован.\n"
                    "Вы можете мгновенно продлить её прямо в меню бота."
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление об истечении пользователю {user_id}: {e}")
                
    # 2. Предупреждение за 1 день до отключения
    one_day_later = (now + timedelta(days=1)).isoformat()
    two_days_later = (now + timedelta(days=2)).isoformat()
    warning_1d_users = await db.get_users_expiring_between(one_day_later, two_days_later)
    for user in warning_1d_users:
        user_id = user["user_id"]
        try:
            await bot.send_message(
                user_id,
                "⏳ Внимание: ваш доступ к VPN заканчивается завтра.\n"
                "Рекомендуем продлить его во избежание автоматического отключения!"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить предупреждение (1 день) пользователю {user_id}: {e}")
            
    # 3. Предупреждение за 3 дня до отключения
    three_days_later = (now + timedelta(days=3)).isoformat()
    four_days_later = (now + timedelta(days=4)).isoformat()
    warning_3d_users = await db.get_users_expiring_between(three_days_later, four_days_later)
    for user in warning_3d_users:
        user_id = user["user_id"]
        try:
            await bot.send_message(
                user_id,
                "ℹ️ Напоминание: ваша VPN подписка истекает через 3 дня. "
                "Вы можете продлить её в меню бота уже сейчас."
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить предупреждение (3 дня) пользователю {user_id}: {e}")

def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    # Фоновый аудит запускается ежедневно в 12:00 по серверному времени
    scheduler.add_job(check_subscriptions_job, 'cron', hour=12, minute=0, args=[bot])
    scheduler.start()
    logger.info("Фоновый планировщик задач успешно запущен.")