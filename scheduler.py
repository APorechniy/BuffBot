# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import db
import config
from x3ui_api import X3UiClient
from aiogram import Bot

async def check_subscriptions_job(bot: Bot):
    now = datetime.now()
    now_str = now.isoformat()
    xui = X3UiClient()
    
    # 1. Заморозка просроченных подписок
    expired_users = await db.get_expired_users(now_str)
    for user in expired_users:
        user_id = user["user_id"]
        client_uuid = user["client_uuid"]
        sub_id = user["sub_id"]
        
        await db.update_user_status(user_id, 'expired')
        
        # Выключаем клиента в 3X-UI
        await xui.update_client_status(
            inbound_id=config.XUI_INBOUND_ID,
            client_uuid=client_uuid,
            email=f"tg_{user_id}",
            sub_id=sub_id,
            enable=False
        )
        
        try:
            await bot.send_message(
                user_id, 
                "⚠️ Срок действия вашего бесплатного/платного доступа истёк.\n"
                "Вы можете продлить его прямо в меню бота."
            )
        except Exception:
            pass
            
    # 2. Предупреждение за 1 день
    one_day_later = (now + timedelta(days=1)).isoformat()
    two_days_later = (now + timedelta(days=2)).isoformat()
    warning_1d_users = await db.get_users_expiring_between(one_day_later, two_days_later)
    for user in warning_1d_users:
        user_id = user["user_id"]
        try:
            await bot.send_message(
                user_id,
                "⏳ Внимание: ваш доступ заканчивается завтра.\n"
                "Продлите его в боте, чтобы не потерять связь."
            )
        except Exception:
            pass

def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_subscriptions_job, 'cron', hour=12, minute=0, args=[bot])
    scheduler.start()