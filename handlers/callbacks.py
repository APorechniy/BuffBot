# handlers/callbacks.py
import uuid
import logging
from aiogram import types, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
import database.db_manager as db
import utils.helpers as helpers
from aiogram.fsm.context import FSMContext
from services.payment_service import ActivePaymentGateway

logger = logging.getLogger("callbacks")

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
    tariffs = helpers.load_tariffs()

    text_lines = [
        "🚀 **ВЫБОР ТАРИФНОГО ПЛАНА**",
        "────────────────────────",
        "Выберите подходящий период подписки. Доступ активируется **мгновенно** после оплаты.\n"
    ]
    keyboard = []

    for tariff_id, tariff in tariffs.items():
        price = tariff["price"]
        days = tariff["days"]
        total_gb = tariff["total_gb"]
        icon = tariff["icon"]
        name = tariff["name"]

        daily_price = round(price / days) if days > 0 else price

        tariff_card = (
            f"{icon} **{name.upper()}**\n"
            f"├ 💳 **Стоимость:** `{price} ₽` _(~{daily_price} ₽/день)_\n"
            f"├ 📊 **Трафик:** `{total_gb} ГБ` _(без урезания скорости)_\n"
            f"├ ⏳ **Срок:** `{days} дней` с момента активации\n"
            f"└ 📱 **Поддержка устройств:** iOS, Android, Windows, macOS\n"
        )
        text_lines.append(tariff_card)

        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} Выбрать {name} — {price} ₽", 
                callback_data=f"buy:{tariff_id}"
            )
        ])

    text_lines.append("────────────────────────")
    text_lines.append(
        "🔒 *Безопасная оплата через СБП, банковские карты и ЮMoney.*\n"
        "💬 *Нужна помощь? Обратитесь в поддержку через главное меню.*"
    )
    keyboard.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")])

    await callback_query.message.edit_text(
        "\n".join(text_lines), 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="Markdown"
    )

async def process_buy_tariff(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    tariff_type = callback_query.data.split(":")[1]

    tariffs = helpers.load_tariffs()
    tariff = tariffs.get(tariff_type)

    if not tariff:
        await callback_query.answer("❌ Выбранный тариф не найден или устарел.", show_alert=True)
        return

    days = tariff["days"]
    minutes = tariff["minutes"]
    amount = tariff["price"]
    tariff_name = tariff["name"]
    total_gb = tariff["total_gb"]

    await callback_query.answer("Формируем заказ...")
    
    # Проверяем FeatureToggle приема платежей
    if settings.PAYMENT_ENABLED:
        order_id = str(uuid.uuid4()) # Генерируем уникальный номер заказа в нашей системе

        admin_message = (
            "🎫 <b>Новый заказ!</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"💬 <b>Тариф:</b>\n{tariff_name}"
            f"<b>OrderID:</b> <code>{order_id}</code>"
        )

        logger.info(f"Регистрация покупки тарифа: user_id={user_id}, days={days}, amount={amount}, order_id={order_id}")
        await bot.send_message(settings.SUPPORT_CHAT_ID, admin_message, parse_mode="HTML")
        # ОБЯЗАТЕЛЬНО: Сначала пишем лог платежа в БД со статусом по умолчанию 'pending'
        await db.save_payment(order_id, user_id, amount)
        
        try:
            gateway = ActivePaymentGateway()
            # На этот адрес платежка пришлет callback-уведомление после оплаты
            hook_url = f"{settings.PAYMENT_WEBHOOK_URL.rstrip('/')}/webhook/payment"
            
            # Вызываем создание счета в платежной системе
            invoice = await gateway.create_invoice(order_id, amount, hook_url)
            
            keyboard = [
                [InlineKeyboardButton(text="💳 Перейти к оплате", url=invoice.payment_url)],
                [InlineKeyboardButton(text="✅ Я оплатил (Проверить)", callback_data=f"check_pay:{order_id}")],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await bot.send_message(
                user_id,
                f"💳 **Счет на оплату тарифа '{tariff_name}' создан!**\n\n"
                f"• **Сумма к оплате:** {amount} руб.\n"
                f"• **Номер заказа:** `{order_id}`\n\n"
                "Нажмите кнопку ниже для проведения безопасного платежа через СБП или банковскую карту.\n\n"
                "Оплатите счет и нажмите кнопку **«Я оплатил»** для мгновенной ручной проверки зачисления."
                "⚠️ *Зачисление обычно происходит в течение 3-5 минут.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception(f"Критическая ошибка при выставлении счета для пользователя {user_id}: {e}")
            await bot.send_message(
                user_id,
                "❌ **Не удалось сформировать ссылку для оплаты.**\n\n"
                "На сервере возникли технические неполадки с платежным шлюзом. "
                "Пожалуйста, обратитесь в службу поддержки через меню бота, мы выпишем счет вручную."
            )
    else:
        # Сценарий бесплатного апгрейда (FeatureToggle=False)
        try:
            sub_link = await helpers.grant_vpn_access(user_id, days, minutes=minutes)
            await bot.send_message(
                user_id,
                f"🎉 **Бесплатный тестовый период на {days} дней успешно активирован!**\n\n"
                f"🔗 Ваша ссылка на подписку:\n`{sub_link}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception(f"Ошибка авто-выдачи доступа без оплаты для {user_id}: {e}")
            await bot.send_message(user_id, f"Произошла техническая ошибка при активации доступа: {e}")

async def process_check_payment(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    order_id = callback_query.data.split(":")[1]
    
    # 1. Извлекаем платеж из локальной БД бота
    payment = await db.get_payment(order_id)
    if not payment:
        await callback_query.answer("Заказ не найден в базе данных бота.", show_alert=True)
        return
        
    # Защита от повторной ручной активации
    if payment['status'] == 'success':
        await callback_query.answer("Этот счет уже был успешно оплачен и зачислен!", show_alert=True)
        return

    await callback_query.answer("Запрос статуса в платежной системе...")
    
    try:
        gateway = ActivePaymentGateway()
        # Вызываем API проверки статуса
        status = await gateway.check_invoice_status(order_id)
        
        if status == "PAID":
            # Активируем подписку (Логика полностью совпадает с вебхуком)
            amount = payment['amount']
            tariffs = helpers.load_tariffs()

            tariff_id = payment.get('tariff_id')
            tariff = tariffs.get(tariff_id) if tariff_id else next((t for t in tariffs.values() if abs(t['price'] - amount) < 1.0), None)
            
            if tariff:
                days = tariff.get("days", 0)
                minutes = tariff.get("minutes", 0)
                total_gb = tariff.get("total_gb", 0)
                tariff_label = tariff.get("name")
            else:
                # Фолбэк на случай, если тариф был удален из JSON
                days, minutes, total_gb, tariff_label = 30, 0, 100, "Стандартный"
                
            logger.info(f"Ручное начисление подписки по кнопке. Пользователь: {user_id}, Дней: {days}, Минуты: {minutes}")
            
            # Закрываем платеж в БД как успешный
            await db.mark_payment_success(order_id)
            
            # Выдаем/продлеваем доступ в панели 3X-UI и БД
            sub_link = await helpers.grant_vpn_access(user_id, days=days, minutes=minutes, total_gb=total_gb)
            
            # Отправляем сообщение пользователю
            await bot.send_message(
                user_id,
                f"🎉 **Оплата успешно подтверждена вручную!**\n\n"
                f"📅 Активирован тариф **'{tariff_label}'**.\n"
                f"🔗 Ваша ссылка на подписку:\n`{sub_link}`",
                parse_mode="Markdown"
            )
            # Удаляем сообщение со старыми кнопками оплаты
            await callback_query.message.delete()
            
        elif status == "NEW":
            await callback_query.answer(
                "⏳ Платеж еще не подтвержден банком.\n\n"
                "Если вы уже провели платеж, пожалуйста, подождите 1-2 минуты и нажмите кнопку проверки снова.", 
                show_alert=True
            )
        elif status == "EXPIRED":
            await db.update_user_status(user_id, 'expired') # помечаем как истекший
            await callback_query.answer("❌ Срок действия этого счета истек. Пожалуйста, выпишите новый счет.", show_alert=True)
        elif status in ("ERROR", "REFUNDED"):
            await callback_query.answer(f"⚠️ Платежная система вернула статус '{status}'. Доступ не может быть зачислен.", show_alert=True)
            
    except Exception as e:
        logger.exception(f"Исключение при ручной проверке статуса платежа {order_id}: {e}")
        await callback_query.answer("Ошибка связи с платежной системой. Попробуйте еще раз позже.", show_alert=True)

async def process_activate_trial_callback(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    success, msg = await helpers.activate_trial_period(user_id, bot)
    if not success:
        await bot.send_message(user_id, f"❌ Ошибка: {msg}")

async def process_show_user_agreement(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ])
    await callback_query.message.edit_text(TERMS_OF_SERVICE_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()

async def process_show_terms(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ])
    await callback_query.message.edit_text(PRIVACY_POLICY_TEXT, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()