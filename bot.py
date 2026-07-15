# bot.py
import sys
import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Принудительно добавляем текущую директорию в PYTHONPATH для корректных импортов в Docker
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
import database.db_manager as db
import scheduler
import handlers.commands as commands
import handlers.callbacks as callbacks
import utils.helpers as helpers

# Инициализация логирования
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
logger = logging.getLogger("main")

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# --- Регистрация хэндлеров Telegram ---
dp.message.register(commands.cmd_start, Command("start"))
dp.callback_query.register(callbacks.process_upgrade_menu, lambda c: c.data == "upgrade_menu")
dp.callback_query.register(callbacks.process_buy_tariff, lambda c: c.data.startswith("buy:"))
dp.callback_query.register(callbacks.process_activate_trial_callback, lambda c: c.data == "activate_trial")
dp.callback_query.register(commands.cmd_start, lambda c: c.data == "back_to_menu") # Назад в меню

# --- API эндпоинты для интеграции с вашим сайтом ---
async def handle_website_trial_api(request):
    """
    Эндпоинт для выдачи триала прямо с сайта.
    Принимает POST JSON: { "tg_id": 123456789 }
    """
    try:
        data = await request.json()
        tg_id = data.get("tg_id")
        if not tg_id:
            return web.json_response({"success": False, "error": "Не указан tg_id"}, status=400)
            
        success, result = await helpers.activate_trial_period(int(tg_id), bot)
        if success:
            return web.json_response({"success": True, "sub_link": result})
        else:
            return web.json_response({"success": False, "error": result}, status=400)
    except Exception as e:
        logger.exception("Ошибка при обработке запроса триала с сайта")
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def start_web_server():
    app = web.Application()
    # API для сайта
    app.router.add_post('/api/trial', handle_website_trial_api)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', settings.WEB_PORT)
    await site.start()
    logger.info(f"Веб-сервер API запущен на порту {settings.WEB_PORT}")

async def main():
    await db.init_db()
    await start_web_server()
    scheduler.start_scheduler(bot)
    
    logger.info("Запуск Telegram-бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())