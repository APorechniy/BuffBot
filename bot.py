# bot.py
import sys
import os
import asyncio
import logging
import html 
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

# Принудительно добавляем текущую директорию в PYTHONPATH для корректных импортов в Docker
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
import database.db_manager as db
import scheduler
import handlers.commands as commands
import handlers.callbacks as callbacks
import utils.helpers as helpers
from services.payment_service import ActivePaymentGateway

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class SupportStates(StatesGroup):
    waiting_for_ticket = State()

# Инициализация логирования
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
logger = logging.getLogger("main")

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

async def handle_payment_webhook(request):
    """
    Принимает входящий вебхук об успешной оплате счета от платежного шлюза.
    """
    logger.info("Получен входящий вебхук от платежной системы.")
    
    headers = dict(request.headers)
    body_bytes = await request.read()
    
    gateway = ActivePaymentGateway()
    
    # 1. Валидируем подпись вебхука
    if not gateway.verify_webhook_signature(body_bytes, headers):
        logger.warning("Запрос вебхука отклонен: неверная подпись сигнатуры.")
        return web.Response(text="Forbidden (Invalid Signature)", status=403)
        
    try:
        # 2. Извлекаем данные
        payload = gateway.parse_webhook(body_bytes, {})
        logger.info(f"Вебхук успешно верифицирован. Номер заказа: {payload.order_id}, Статус: {payload.status}")
        
        if payload.status == "success":
            success = await helpers.process_successful_payment(payload.order_id, bot)
            if not success:
                return web.Response(text="Order not found", status=404)
                    
        # Платежка ожидает получить статус 200 OK в ответ на вебхук
        return web.Response(text="OK", status=200)
        
    except Exception as e:
        logger.exception(f"Исключение при обработке вебхука платежа: {e}")
        return web.Response(text="Internal Server Error", status=500)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="terms", description="Пользовательское соглашение"),
        BotCommand(command="privacy", description="Политика конфиденциальности"),
    ]
    await bot.set_my_commands(commands)

async def back_to_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    # Возвращаем пользователя в главное меню
    await commands.cmd_start(callback_query.message)

@dp.callback_query(lambda c: c.data == "cancel_support")
async def process_cancel_support(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear() # Сбрасываем состояние FSM
    await callback_query.answer("Отправка обращения отменена.")
    # Возвращаем пользователя в главное меню
    await commands.cmd_start(callback_query.message)

# Хэндлер приема текста обращения
@dp.message(SupportStates.waiting_for_ticket)
async def handle_support_message(message: types.Message, state: FSMContext):
    # Сразу сбрасываем состояние, чтобы пользователь мог дальше пользоваться командами
    await state.clear()
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
    
    # Экранируем все данные, пришедшие от пользователя, защищая разметку от падений
    full_name_safe = html.escape(message.from_user.full_name)
    username_safe = html.escape(username)
    ticket_text_safe = html.escape(message.text)
    
    # Формируем сообщение для админов, используя безопасные HTML-теги вместо Markdown
    admin_message = (
        "🎫 <b>Новое обращение в техподдержку!</b>\n\n"
        f"👤 <b>Отправитель:</b> {full_name_safe}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🗣️ <b>Логин:</b> {username_safe}\n\n"
        f"💬 <b>Текст обращения:</b>\n{ticket_text_safe}"
    )
    
    # Отправляем сообщение в чат поддержки
    try:
        if settings.SUPPORT_CHAT_ID == 0:
            raise Exception("Не настроен SUPPORT_CHAT_ID в файле .env")
            
        await bot.send_message(settings.SUPPORT_CHAT_ID, admin_message, parse_mode="HTML")
        
        # Подтверждение пользователю
        keyboard = [[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")]]
        await message.answer(
            "✅ <b>Ваше обращение успешно зарегистрировано!</b>\n\n"
            "Инженеры поддержки уже изучают вашу проблему. Мы свяжемся с вами в ближайшее время.\n"
            "Спасибо!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Не удалось перенаправить обращение в чат поддержки: {e}")
        keyboard = [[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")]]
        await message.answer(
            "❌ <b>Произошла техническая ошибка при отправке.</b>\n\n"
            "К сожалению, сейчас мы не смогли доставить ваше сообщение. Пожалуйста, напишите ваше обращение "
            "напрямую на наш почтовый ящик <code>beunaffected@mail.ru</code>.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
async def process_start_support(callback_query: types.CallbackQuery, state: FSMContext):
    """Инициализирует процесс отправки тикета, переключая FSM."""
    await callback_query.answer()
    
    # Включаем состояние ожидания ввода сообщения
    await state.set_state(SupportStates.waiting_for_ticket)
    
    text = (
        "💬 **Служба технической поддержки**\n\n"
        "Вы можете оставить обращение прямо здесь. Напишите текст вашей проблемы в одном сообщении "
        "и отправьте его в этот чат — бот автоматически передаст его дежурным инженерам.\n\n"
        "Также вы можете отправить подробное письмо на наш EMail: `beunaffected@mail.ru` "
        "с обязательным указанием вашего логина (Username) в Telegram.\n\n"
        "✍️ **Отправьте ваше сообщение прямо сейчас (или нажмите 'Отмена'):**"
    )
    keyboard = [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")]]
    await callback_query.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")


# --- Регистрация хэндлеров Telegram ---
dp.message.register(commands.cmd_start, Command("start"))
dp.message.register(commands.cmd_privacy, Command("privacy"))
dp.message.register(commands.cmd_terms, Command("terms"))
dp.callback_query.register(callbacks.process_upgrade_menu, lambda c: c.data == "upgrade_menu")
dp.callback_query.register(callbacks.process_buy_tariff, lambda c: c.data.startswith("buy:"))
dp.callback_query.register(callbacks.process_check_payment, lambda c: c.data.startswith("check_pay:"))
dp.callback_query.register(callbacks.process_activate_trial_callback, lambda c: c.data == "activate_trial")
dp.callback_query.register(callbacks.process_show_docs, lambda c: c.data == "show_docs")
dp.callback_query.register(callbacks.process_show_user_agreement, lambda c: c.data == "show_user_agreement")
dp.callback_query.register(callbacks.process_show_terms, lambda c: c.data == "show_terms")
dp.callback_query.register(callbacks.process_show_inst, lambda c: c.data.startswith("inst_"))
dp.callback_query.register(process_start_support, lambda c: c.data == "start_support_ticket")
dp.callback_query.register(back_to_menu, lambda c: c.data == "back_to_menu") # Назад в меню

# --- API эндпоинты для интеграции с вашим сайтом ---
async def handle_website_trial_api(request):
    """
    Эндпоинт для выдачи триала прямо с сайта.
    Выдается на 30 минут, после чего умирает.
    Цель - заманить клиента в бота
    """
    try:
        client_secret = request.headers.get("X-Internal-Secret", "")

        if not helpers.verify_internal_token(client_secret=client_secret):
            return web.json_response({"success": False, "error": "Доступ запрещен"}, status=403)

        success, result = await helpers.create_temp_user(bot)
        if success:
            return web.json_response({"success": True, "subscription_url": result})
        else:
            return web.json_response({"success": False, "error": result}, status=400)
    except Exception as e:
        logger.exception("Ошибка при обработке запроса триала с сайта")
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def start_web_server():
    app = web.Application()
    # API для сайта
    app.router.add_post('/api/trial', handle_website_trial_api)
    app.router.add_post('/webhook/payment', handle_payment_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', settings.WEB_PORT)
    await site.start()
    logger.info(f"Веб-сервер API запущен на порту {settings.WEB_PORT}")

async def main():
    await db.init_db()
    await start_web_server()
    scheduler.start_scheduler(bot)
    set_bot_commands(bot)
    
    logger.info("Запуск Telegram-бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())