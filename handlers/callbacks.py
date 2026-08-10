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
from constants.texts import PRIVACY_POLICY_TEXT, TERMS_OF_SERVICE_TEXT, DOCUMENTATION
from constants.instructions import IOS_INSTRUCTION, ANDROID_INSTRUCTION, WINDOWS_INSTRUCTION

logger = logging.getLogger("callbacks")

async def process_show_inst(callback_query: types.CallbackQuery):
    """Показывает подробную инструкцию по настройке VPN для выбранной ОС."""
    platform = callback_query.data.split("_")[1]
    
    text = ""
    keyboard = []

    if platform == "ios":
        text = IOS_INSTRUCTION
        keyboard = [
            [InlineKeyboardButton(text="📥 Скачать V2RAGE (App Store)", url="https://apps.apple.com/ru/app/v2rage/id6761075402")],
            [InlineKeyboardButton(text="🔙 К выбору ОС", callback_data="show_docs")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]

    elif platform == "android":
        text = ANDROID_INSTRUCTION
        keyboard = [
            [InlineKeyboardButton(text="📥 Скачать v2rayNG (Google Play)", url="https://play.google.com/store/apps/details?id=com.v2ray.ang")],
            [InlineKeyboardButton(text="🔙 К выбору ОС", callback_data="show_docs")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]

    elif platform == "windows":
        text = WINDOWS_INSTRUCTION
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
    
    keyboard = [
        [InlineKeyboardButton(text="🍏 iOS (iPhone / iPad)", callback_data="inst_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="inst_android")],
        [InlineKeyboardButton(text="💻 Windows (ПК)", callback_data="inst_windows")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ]
    await callback_query.message.edit_text(
        DOCUMENTATION, 
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
    tariff_id = tariff["id"]
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
        await db.save_payment(order_id, user_id, amount, tariff_id)
        
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
    payment_row = await db.get_payment(order_id)
    if not payment_row:
        await callback_query.answer("Заказ не найден в базе данных бота.", show_alert=True)
        return

    payment = dict(payment_row)
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
            await helpers.process_successful_payment(order_id, bot)
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