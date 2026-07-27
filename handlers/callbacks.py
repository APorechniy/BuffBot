# handlers/callbacks.py
import uuid
from aiogram import types, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
import database.db_manager as db
import utils.helpers as helpers
from aiogram.fsm.context import FSMContext

# ==========================================
# ТЕКСТЫ ДОКУМЕНТОВ
# ==========================================
PRIVACY_POLICY_TEXT = (
    "🔒 **Политика конфиденциальности сервиса Buff VPN**\n\n"
    "Настоящая Политика описывает, как сервис **Buff VPN** обрабатывает информацию пользователей.\n\n"
    "**1. Сбор и хранение данных (No-Logs Policy)**\n"
    "Мы придерживаемся политики строгой конфиденциальности и минимизации данных:\n"
    "• **Единственные данные, которые мы храним:** ваш уникальный числовой идентификатор **Telegram User ID**.\n"
    "• Он используется исключительно для привязки статуса подписки к вашему аккаунту и сгенерированной ссылки.\n\n"

    "**2. Что мы НЕ собираем и НЕ храним:**\n"
    "❌ Мы **не храним** логи вашей сетевой активности (посещенные сайты, время, трафик).\n"
    "❌ Мы **не знаем** ваш реальный IP-адрес, имя, фамилию или номер телефона.\n"
    "❌ Мы **не храним** платежные данные. Все транзакции проходят на стороне аккредитованных платежных шлюзов.\n\n"

    "**3. Защита данных**\n"
    "Ваш Telegram ID не передается третьим лицам и используется только внутри бота для проверки наличия активного тарифа.\n\n"

    "**4. Изменения**\n"
    "Сервис оставляет за собой право обновлять настоящую политику. Актуальная версия всегда доступна по команде /privacy."
)

TERMS_OF_SERVICE_TEXT = (
    "📜 **Пользовательское соглашение (Terms of Service)**\n\n"
    "Используя сервис **Buff VPN**, вы соглашаетесь с нижеследующими условиями:\n\n"

    "**1. Предоставление услуг**\n"
    "• Сервис предоставляет доступ к приватным узлам связи по подписке.\n"
    "• Услуги предоставляются по принципу «Как есть» (As Is). Мы гарантируем максимальную доступность серверов, но не несем ответственности за форс-мажоры или блокировки со стороны магистральных провайдеров.\n\n"

    "**2. Правила использования и запреты**\n"
    "При использовании VPN-сервиса **строго запрещено:**\n"
    "🚫 Совершение любых действий, нарушающих законодательство.\n"
    "🚫 Проведение DDoS-атак, сканирование портов, спам-рассылки.\n"
    "🚫 Распространение вредоносного ПО и фишинг.\n"
    "⚠️ В случае выявления нарушений доступ к сервису аннулируется без возврата средств.\n\n"

    "**3. Идентификация пользователя**\n"
    "• Сервис не проводит процедуру KYC (верификацию личности).\n"
    "• Единственным идентификатором вашего аккаунта является ваш **Telegram ID**.\n\n"

    "**4. Оплата и возврат**\n"
    "• Оплата производится за фиксированный период доступа (30/90 дней).\n"
    "• Возврат средств возможен только в случае, если сервис не предоставлял услугу по техническим причинам на нашей стороне более 48 часов подряд."
)

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
    """Открывает подробную документацию и развилку выбора ОС."""
    text = (
        "📖 **Документация по проекту Buff VPN**\n\n"
        "**Buff VPN** — это сервис безопасного и шифрованного сетевого подключения, "
        "предназначенный для обеспечения конфиденциальности передаваемых данных и защиты "
        "пользователей при работе в незащищённых сетях.\n\n"
        "🛡 **Ключевые функции сервиса:**\n"
        "• **Шифрование трафика:** Защита ваших паролей, банковских данных и личной переписки от перехвата при подключении к публичным сетям Wi-Fi (в кафе, отелях, аэропортах).\n"
        "• **Конфиденциальность:** Защита сетевого соединения от коммерческого трекинга, сбора метрик и аналитики сторонними сервисами.\n"
        "• **Защищённый туннель:** Использование современных стойких протоколов шифрования, обеспечивающих высокую скорость и стабильность соединения.\n\n"
        "⚠️ **Юридическая информация и правила использования:**\n"
        "Сервис Buff VPN создан исключительно для обеспечения безопасности и защиты персональной информации.\n"
        "• Сервис **не предназначен** и **не используется** для обхода технических ограничений доступа, установленных законодательством.\n"
        "• Сервис **не предоставляет** возможности для обхода локальных сетевых правил («белых» и «черных» списков адресов) или фильтрации трафика.\n"
        "• Пользователь обязуется использовать сервис в строгом соответствии с действующим законодательством.\n\n"
        "📲 **Инструкции по настройке:**\n"
        "Выберите ваше устройство из списка ниже, чтобы получить пошаговое руководство по настройке клиенского подключения:"
    )
    keyboard = [
        [InlineKeyboardButton(text="🍏 iOS (iPhone / iPad)", callback_data="inst_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="inst_android")],
        [InlineKeyboardButton(text="💻 Windows (ПК)", callback_data="inst_windows")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ]
    await callback_query.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="Markdown"
    )
    
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

async def process_show_user_agreement(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Пользовательское соглашение", callback_data="show_terms_callback")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ])
    await callback_query.message.edit_text(PRIVACY_POLICY_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()

async def process_show_terms(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="show_privacy_callback")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ])
    await callback_query.message.edit_text(TERMS_OF_SERVICE_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()