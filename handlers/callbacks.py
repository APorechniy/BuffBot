# handlers/callbacks.py
import uuid
from aiogram import types, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
import database.db_manager as db
import utils.helpers as helpers
from aiogram.fsm.context import FSMContext

async def process_show_inst(callback_query: types.CallbackQuery):
    """Показывает подробную инструкцию по настройке VPN для выбранной ОС."""
    platform = callback_query.data.split("_")[1]
    
    text = ""
    keyboard = []

    if platform == "ios":
        text = (
            "🍏 **Инструкция по настройке для iOS (iPhone / iPad)**\n\n"
            "📱 **Рекомендуемый клиент:** **V2RAGE** или **NpvTunnel**\n\n"
            "**Пошаговая настройка (на примере V2RAGE):**\n"
            "1. Скачайте и установите приложение по кнопке ниже.\n"
            "2. Скопируйте вашу **ссылку на подписку** (из Личного кабинета бота).\n"
            "3. Откройте приложение **V2RAGE** и нажмите **`+`** в правом верхнем углу.\n"
            "4. Нажмите **«Вставить»**, ваша ссылка должна прикрепиться.\n"
            "5. Выберите появившийся сервер и переключите ползунок для подключения.\n\n"
            "💡 *При обновлении подписки приложение будет автоматически получать свежие рабочие узлы.*"
        )
        keyboard = [
            [InlineKeyboardButton(text="📥 Скачать V2RAGE (App Store)", url="https://apps.apple.com/ru/app/v2rage/id6761075402")],
            [InlineKeyboardButton(text="🔙 К выбору ОС", callback_data="show_docs")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]

    elif platform == "android":
        text = (
            "🤖 **Инструкция по настройке для Android**\n\n"
            "📱 **Рекомендуемый клиент:** **v2rayNG** (Бесплатный, стабильный клиент из Google Play)\n\n"
            "**Пошаговая настройка:**\n"
            "1. Установите приложение **v2rayNG** из Google Play / RuStore.\n"
            "2. Скопируйте вашу **ссылку на подписку** (из Личного кабинета бота).\n"
            "3. Откройте **v2rayNG**, нажмите на меню **`≡`** (слева вверху) ➔ **«Настройки групп подписок»**.\n"
            "4. Нажмите **`+`** (вверху), введите имя (например `Buff VPN`) и вставьте вашу ссылку в поле **«URL»**.\n"
            "5. Сохраните (галочка вверху справа) и вернитесь на главный экран.\n"
            "6. Нажмите **три точки** (справа вверху) ➔ **«Обновить подписку»**.\n"
            "7. Нажмите на кружок с галочкой внизу справа для подключения."
        )
        keyboard = [
            [InlineKeyboardButton(text="📥 Скачать v2rayNG (Google Play)", url="https://play.google.com/store/apps/details?id=com.v2ray.ang")],
            [InlineKeyboardButton(text="🔙 К выбору ОС", callback_data="show_docs")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]

    elif platform == "windows":
        text = (
            "💻 **Инструкция по настройке для Windows**\n\n"
            "💻 **Рекомендуемый клиент:** **v2rayN** или **NekoBox**\n\n"
            "**Пошаговая настройка (v2rayN):**\n"
            "1. Скачайте и распакуйте архив с приложением **v2rayN** (нужен файл `v2rayN-With-Core.zip`).\n"
            "2. Скопируйте вашу **ссылку на подписку** (из Личного кабинета бота).\n"
            "3. Запустите `v2rayN.exe`.\n"
            "4. Нажмите сверху вкладку **«Подписка» (Subscription)** ➔ **«Настройка групп подписок»**.\n"
            "5. Нажмите **«Добавить»**, введите имя `Buff VPN`, вставьте вашу ссылку в поле **«URL»** и нажмите **«Сохранить»**.\n"
            "6. Вернитесь в главное окно, откройте **«Подписка»** ➔ **«Обновить подписку»** (или `Ctrl+O`).\n"
            "7. В нижней панели приложения переключите **«Системный прокси» (System Proxy)** в режим **«Включить» (Set system proxy)**."
        )
        keyboard = [
            [InlineKeyboardButton(text="📥 Скачать v2rayN (GitHub)", url="https://github.com/2dust/v2rayN/releases")],
            [InlineKeyboardButton(text="🔙 К выбору ОС", callback_data="show_docs")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]

    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await callback_query.answer()

async def process_show_docs(callback_query: types.CallbackQuery):
    """Открывает краткую документацию и развилку выбора ОС."""
    text = (
        "📖 **Документация по проекту Buff VPN**\n\n"
        "Наш сервис создан для того, чтобы ваша работа в интернете оставалась быстрой и"
        "конфиденциальной. Соединение работает так, что внешне оно неотличимо от обычного просмотра сайтов. \n\n"
        "Выберите ваше устройство из списка ниже, и мы сразу пришлём простую пошаговую инструкцию для начала работы:"
    )
    keyboard = [
        [InlineKeyboardButton(text="🍏 iOS (iPhone / iPad)", callback_data="inst_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="inst_android")],
        [InlineKeyboardButton(text="💻 Windows (ПК)", callback_data="inst_windows")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

async def process_upgrade_menu(callback_query: types.CallbackQuery):
    """Показывает тарифную сетку для покупки/продления."""
    text = (
        "💎 **Выберите тарифный план для активации/продления:**\n\n"
        f"• **1 месяц (30 дней)** — {settings.PRICE_30_DAYS} руб.\n"
        f"• **3 месяца (90 дней)** — {settings.PRICE_90_DAYS} руб.\n\n"
        "После выбора вы будете перенаправлены на страницу оплаты."
    )
    keyboard = [
        [
            InlineKeyboardButton(text=f"💎 1 месяц — {settings.PRICE_30_DAYS} р.", callback_data="buy:30"),
            InlineKeyboardButton(text=f"👑 3 месяца — {settings.PRICE_90_DAYS} р.", callback_data="buy:90")
        ],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
    ]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

async def process_buy_tariff(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    days = int(callback_query.data.split(":")[1])
    amount = settings.PRICE_30_DAYS if days == 30 else settings.PRICE_90_DAYS
    
    await callback_query.answer("Обработка тарифа...")
    
    if settings.PAYMENT_ENABLED:
        # Платный сценарий
        order_id = str(uuid.uuid4())
        await db.save_payment(order_id, user_id, amount)
        # Здесь будет генерация ссылки через payment_service
        await bot.send_message(user_id, "Генерация счета отключена. Обратитесь в поддержку.")
    else:
        # Бесплатный сценарий (FeatureToggle) - мгновенный апгрейд
        try:
            sub_link = await helpers.grant_vpn_access(user_id, days)
            await bot.send_message(
                user_id,
                f"🎉 **Тариф успешно активирован на {days} дней!**\n\n"
                f"🔗 Ссылка на подписку:\n`{sub_link}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            await bot.send_message(user_id, f"Произошла ошибка при апгрейде тарифа: {e}")

async def process_activate_trial_callback(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    success, msg = await helpers.activate_trial_period(user_id, bot)
    if not success:
        await bot.send_message(user_id, f"❌ Ошибка: {msg}")