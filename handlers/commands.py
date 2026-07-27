# handlers/commands.py
from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

import database.db_manager as db
from config import settings

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

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
    "📜 **Пользовательское соглашение**\n\n"
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

# ==========================================
# ОБРАБОТЧИКИ КОМАНД
# ==========================================
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = await db.create_or_get_user(user_id)
    
    status = user['status']
    expires_at = user['expires_at']
    sub_id = user['sub_id']
    trial_used = user['trial_used']
    
    text = "🛡️ **Главное меню Buff VPN**\n\n"
    keyboard = []
    
    if status == 'active' and expires_at:
        expiry_dt = datetime.fromisoformat(expires_at)
        sub_link = f"{settings.XUI_SUB_BASE_URL.rstrip('/')}/buff-subscribe/{sub_id}"
        text += (
            f"✅ **Статус:** Активен\n"
            f"📅 **Истекает:** {expiry_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔗 **Ссылка подписки:**\n`{sub_link}`"
        )
        keyboard.append([InlineKeyboardButton(text="🚀 Инструкции", callback_data="show_instructions")])
        keyboard.append([InlineKeyboardButton(text="💎 Апгрейд / Продлить тариф", callback_data="upgrade_menu")])
    else:
        text += "❌ **Статус:** Доступ отсутствует.\n\n"
        if trial_used == 0:
            text += "🎁 Вам доступен бесплатный тест на 1 день!"
            keyboard.append([InlineKeyboardButton(text="🎁 Активировать тест (1 день)", callback_data="activate_trial")])
        
        keyboard.append([InlineKeyboardButton(text="💳 Оформить подписку", callback_data="upgrade_menu")])

    keyboard.append([InlineKeyboardButton(text="📋 Пользовательское соглашение", callback_data="show_user_agreement")])
    keyboard.append([InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="show_terms")])
    keyboard.append([InlineKeyboardButton(text="📖 Документация по проекту", callback_data="show_docs")])
    keyboard.append([InlineKeyboardButton(text="💬 Техподдержка", callback_data="start_support_ticket")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

async def cmd_privacy(message: types.Message):
    """Показывает политику конфиденциальности."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ])
    await message.answer(PRIVACY_POLICY_TEXT, reply_markup=keyboard, parse_mode="Markdown")

async def cmd_terms(message: types.Message):
    """Показывает пользовательское соглашение."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ])
    await message.answer(TERMS_OF_SERVICE_TEXT, reply_markup=keyboard, parse_mode="Markdown")