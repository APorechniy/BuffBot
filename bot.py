# bot.py
import sys
import os
import asyncio
import logging
import html 
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Принудительно добавляем текущую директорию в PYTHONPATH для корректных импортов в Docker
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
import database.db_manager as db
import scheduler
import handlers.commands as commands
import handlers.callbacks as callbacks
import utils.helpers as helpers

class SupportStates(StatesGroup):
    waiting_for_ticket = State()

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
logger = logging.getLogger("main")

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# Обработчик отмены поддержки
@dp.callback_query(lambda c: c.data == "cancel_support")
async def process_cancel_support(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.answer("Отправка отменена.")
    await commands.cmd_start(callback_query)

# Хэндлер приема текста обращения
@dp.message(SupportStates.waiting_for_ticket)
async def handle_support_message(message: types.Message, state: FSMContext):
    # ПРОВЕРКА: Если отправлен не текст (например, фото/стикер)
    if not message.text:
        await message.answer("⚠️ Пожалуйста, опишите вашу проблему **текстовым сообщением**.")
        return

    await state.clear()
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
    
    full_name_safe = html.escape(message.from_user.full_name)
    username_safe = html.escape(username)
    ticket_text_safe = html.escape(message.text)
    
    admin_message = (
        "🎫 <b>Новое обращение в техподдержку!</b>\n\n"
        f"👤 <b>Отправитель:</b> {full_name_safe}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🗣️ <b>Логин:</b> {username_safe}\n\n"
        f"💬 <b>Текст обращения:</b>\n{ticket_text_safe}"
    )
    
    try:
        if settings.SUPPORT_CHAT_ID == 0:
            raise Exception("SUPPORT_CHAT_ID не настроен")
            
        await bot.send_message(settings.SUPPORT_CHAT_ID, admin_message, parse_mode="HTML")
        
        keyboard = [[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")]]
        await message.answer(
            "✅ <b>Ваше обращение успешно зарегистрировано!</b>\n\n"
            "Инженеры поддержки уже изучают проблему. Мы свяжемся с вами в этом чате.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Не удалось перенаправить обращение: {e}")
        keyboard = [[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")]]
        await message.answer(
            "❌ <b>Ошибка при отправке.</b>\n\n"
            "Напишите напрямую на почту: <code>beunaffected@mail.ru</code>.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

async def process_start_support(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(SupportStates.waiting_for_ticket)
    
    text = (
        "💬 **Служба технической поддержки**\n\n"
        "Напишите текст вашей проблемы в одном сообщении и отправьте в этот чат.\n\n"
        "✍️ **Отправьте сообщение прямо сейчас:**"
    )
    keyboard = [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")]]
    await callback_query.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")


# --- Регистрация хэндлеров Telegram ---
dp.message.register(commands.cmd_start, Command("start"))
dp.callback_query.register(commands.cmd_start, lambda c: c.data == "back_to_menu")
dp.callback_query.register(callbacks.process_upgrade_menu, lambda c: c.data == "upgrade_menu")
dp.callback_query.register(callbacks.process_buy_tariff, lambda c: c.data.startswith("buy:"))
dp.callback_query.register(callbacks.process_activate_trial_callback, lambda c: c.data == "activate_trial")
dp.callback_query.register(callbacks.process_show_docs, lambda c: c.data == "show_docs")
dp.callback_query.register(callbacks.process_show_docs, lambda c: c.data == "show_instructions")
dp.callback_query.register(callbacks.process_instruction_detail, lambda c: c.data.startswith("inst_"))
dp.callback_query.register(process_start_support, lambda c: c.data == "start_support_ticket")

# Web Server & Main
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