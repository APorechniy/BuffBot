# bot.py
import asyncio
import uuid
import secrets
import json
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
import db
from x3ui_api import X3UiClient
import scheduler

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# --- Инструкции для разных OS ---
INSTRUCTIONS = {
    "ios": (
        "🍏 **Инструкция для iOS (iPhone / iPad):**\n\n"
        "1. Установите приложение **V2Box** или **FoXray** из App Store.\n"
        "2. Скопируйте вашу персональную ссылку на подписку из бота.\n"
        "3. Откройте приложение, перейдите в раздел 'Configs' -> нажмите '+' -> выберите 'Import Subscription Group' / 'Add subscription'.\n"
        "4. Вставьте скопированную ссылку подписки и сохраните.\n"
        "5. Проведите пальцем сверху вниз по списку, чтобы обновить конфигурации, выберите самый быстрый сервер и нажмите кнопку подключения!"
    ),
    "android": (
        "🤖 **Инструкция для Android:**\n\n"
        "1. Установите приложение **v2rayNG** или **NekoBox** из Google Play.\n"
        "2. Скопируйте ссылку на подписку из бота.\n"
        "3. Откройте приложение v2rayNG -> нажмите на иконку 'три полоски' слева -> выберите 'Группы подписок' -> нажмите '+' -> Вставьте название и вашу ссылку подписки.\n"
        "4. Вернитесь на главный экран -> нажмите 'три точки' справа вверху -> выберите 'Обновить подписки'.\n"
        "5. Выберите один из появившихся серверов и нажмите круглую кнопку внизу для подключения!"
    ),
    "windows": (
        "💻 **Инструкция для Windows:**\n\n"
        "1. Скачайте программу **v2rayN** или **NekoBox для ПК** с GitHub.\n"
        "2. Скопируйте ссылку на подписку.\n"
        "3. В программе перейдите в меню 'Подписка' -> 'Настройка подписок' -> нажмите 'Добавить' -> вставьте ссылку.\n"
        "4. Нажмите 'Подписка' -> 'Обновить подписку'.\n"
        "5. Выберите любой сервер из списка, нажмите Enter и переведите системный режим в 'Проксировать всё'."
    )
}

# --- Логика активации доступа ---

async def grant_vpn_access(user_id: int) -> str:
    """Генерирует профиль в базе данных и автоматически заводит клиента в 3X-UI."""
    user = await db.get_user(user_id)
    client_uuid = user['client_uuid'] if (user and user['client_uuid']) else str(uuid.uuid4())
    sub_id = user['sub_id'] if (user and user['sub_id']) else secrets.token_hex(8)
    client_email = f"tg_{user_id}"
    
    # Продлеваем/активируем доступ на 30 дней бесплатно/платно в БД
    new_expiry = await db.activate_user_subscription(user_id, client_uuid, sub_id, days=30)
    
    # Регистрируем в локальной панели 3X-UI
    xui = X3UiClient()
    success = await xui.add_client(
        inbound_id=config.XUI_INBOUND_ID,
        email=client_email,
        client_uuid=client_uuid,
        sub_id=sub_id
    )
    
    # Если клиент уже был в панели, но был выключен — размораживаем его
    if not success:
        await xui.update_client_status(
            inbound_id=config.XUI_INBOUND_ID,
            client_uuid=client_uuid,
            email=client_email,
            sub_id=sub_id,
            enable=True
        )
        
    return f"{config.XUI_SUB_BASE_URL.rstrip('/')}/sub/{sub_id}"

# --- Обработчики команд ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = await db.create_or_get_user(user_id)
    
    status = user['status']
    expires_at = user['expires_at']
    sub_id = user['sub_id']
    
    text = "👋 Добро пожаловать в сервис приватного скоростного VPN!\n\n"
    keyboard = []
    
    if status == 'active' and expires_at:
        expiry_dt = datetime.fromisoformat(expires_at)
        sub_link = f"{config.XUI_SUB_BASE_URL.rstrip('/')}/sub/{sub_id}"
        text += (
            f"✅ Ваш доступ активен!\n"
            f"📅 Действует до: {expiry_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔗 Персональная ссылка на подписку:\n`{sub_link}`\n\n"
            "Используйте кнопки ниже, чтобы посмотреть инструкции по настройке на устройствах."
        )
        keyboard.append([InlineKeyboardButton(text="📖 Инструкция по установке", callback_data="show_instructions")])
        if config.PAYMENT_ENABLED:
            keyboard.append([InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="buy_sub")])
        else:
            keyboard.append([InlineKeyboardButton(text="🔄 Обновить доступ", callback_data="get_free_vpn")])
    else:
        # FEATURE TOGGLE в действии:
        if config.PAYMENT_ENABLED:
            text += (
                f"Для получения доступа необходимо приобрести подписку.\n"
                f"💵 Стоимость: {config.SUB_PRICE} руб. / 30 дней."
            )
            keyboard.append([InlineKeyboardButton(text="💳 Купить доступ (30 дней)", callback_data="buy_sub")])
        else:
            text += (
                "У нас отличные новости! На данный момент доступ к нашему качественному VPN предоставляется **совершенно бесплатно**.\n\n"
                "Нажмите кнопку ниже, чтобы получить личную ссылку подписки."
            )
            keyboard.append([InlineKeyboardButton(text="🚀 Получить бесплатный доступ", callback_data="get_free_vpn")])
            
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "get_free_vpn")
async def process_get_free_vpn(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.answer("Генерируем ваш ключ доступа...")
    
    try:
        sub_link = await grant_vpn_access(user_id)
        
        keyboard = [
            [InlineKeyboardButton(text="📖 Инструкции по настройке", callback_data="show_instructions")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await bot.send_message(
            user_id,
            f"🎉 Ваш профиль успешно создан!\n\n"
            f"🔗 **Ваша ссылка подписки:**\n`{sub_link}`\n\n"
            f"⚠️ *Не делитесь ссылкой с посторонними, она привязана лично к вам.*",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await bot.send_message(user_id, f"Произошла ошибка при создании ключа. Обратитесь в поддержку: {e}")

# --- Интерактивные инструкции в боте ---

@dp.callback_query(lambda c: c.data == "show_instructions")
async def show_instructions_menu(callback_query: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🍏 iOS (iPhone / iPad)", callback_data="inst_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="inst_android")],
        [InlineKeyboardButton(text="💻 Windows (ПК)", callback_data="inst_windows")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await bot.send_message(
        callback_query.from_user.id,
        "Выберите операционную систему вашего устройства:",
        reply_markup=reply_markup
    )
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("inst_"))
async def process_os_instruction(callback_query: types.CallbackQuery):
    os_name = callback_query.data.split("_")[1]
    text = INSTRUCTIONS.get(os_name, "Инструкция не найдена.")
    
    keyboard = [[InlineKeyboardButton(text="🔙 К выбору ОС", callback_data="show_instructions")]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await bot.send_message(callback_query.from_user.id, text, reply_markup=reply_markup, parse_mode="Markdown")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    # Создаем симуляцию входящего текстового сообщения для перехода на главный экран
    message = callback_query.message
    message.from_user = callback_query.from_user
    await cmd_start(message)

# --- Системный платный функционал (Отработка FeatureToggle) ---

@dp.callback_query(lambda c: c.data == "buy_sub")
async def process_buy_sub(callback_query: types.CallbackQuery):
    if not config.PAYMENT_ENABLED:
        await callback_query.answer("Продажи сейчас отключены, используйте бесплатный доступ!", show_alert=True)
        return
    # Если платежка включена, здесь вы создаете инвойс с помощью динамически подключенного шлюза
    await callback_query.answer("Платежная система не настроена.", show_alert=True)

# --- Вебхук сервер ---

async def handle_payment_webhook(request):
    """Слушатель вебхуков для будущего эквайринга."""
    if not config.PAYMENT_ENABLED:
        return web.Response(text="Payments disabled", status=400)
    # Здесь будет выполняться валидация через payment_interface
    return web.Response(text="OK", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_post('/webhook/payment', handle_payment_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.WEB_PORT)
    await site.start()
    print(f"Webhook server started on port {config.WEB_PORT}")

async def main():
    await db.init_db()
    await start_web_server()
    scheduler.start_scheduler(bot)
    
    print("Starting bot in free/paid toggle mode...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())