# handlers/commands.py
import secrets
from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

import database.db_manager as db
from config import settings

from constants.texts import PRIVACY_POLICY_TEXT, TERMS_OF_SERVICE_TEXT
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

# ==========================================
# ОБРАБОТЧИКИ КОМАНД
# ==========================================
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = await db.create_or_get_user(user_id, sub_id=secrets.token_hex(8))
    
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