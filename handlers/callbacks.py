# handlers/callbacks.py
import uuid
from aiogram import types, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
import database.db_manager as db
import utils.helpers as helpers
from aiogram.fsm.context import FSMContext
from bot import SupportStates, bot
from handlers import commands

# Хэндлер отмены заполнения обращения
async def process_cancel_support(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear() # Сбрасываем состояние FSM
    await callback_query.answer("Отправка обращения отменена.")
    # Возвращаем пользователя в главное меню
    await commands.cmd_start(callback_query.message)

# Хэндлер приема текста обращения
async def handle_support_message(message: types.Message, state: FSMContext):
    # Сразу сбрасываем состояние, чтобы пользователь мог дальше пользоваться командами
    await state.clear()
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
    full_name = message.from_user.full_name
    ticket_text = message.text
    
    # Формируем красивое сообщение для вашей закрытой группы администраторов
    admin_message = (
        "🎫 **Новое обращение в техподдержку!**\n\n"
        f"👤 **Отправитель:** {full_name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"🗣️ **Логин:** {username}\n\n"
        f"💬 **Текст обращения:**\n_\"{ticket_text}\"_"
    )
    
    # Отправляем сообщение в чат поддержки
    try:
        if settings.SUPPORT_CHAT_ID == 0:
            raise Exception("Не настроен SUPPORT_CHAT_ID в файле .env")
            
        await bot.send_message(settings.SUPPORT_CHAT_ID, admin_message, parse_mode="Markdown")
        
        # Подтверждение пользователю
        keyboard = [[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")]]
        await message.answer(
            "✅ **Ваше обращение успешно зарегистрировано!**\n\n"
            "Инженеры поддержки уже изучают вашу проблему. Мы свяжемся с вами в ближайшее время прямо здесь, в чате бота.\n"
            "Спасибо!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        keyboard = [[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")]]
        await message.answer(
            "❌ **Произошла техническая ошибка при отправке.**\n\n"
            "К сожалению, сейчас мы не смогли доставить ваше сообщение. Пожалуйста, напишите ваше обращение "
            "напрямую на наш почтовый ящик `beunaffected@mail.ru`.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )


async def process_show_docs(callback_query: types.CallbackQuery):
    """Открывает краткую документацию и развилку выбора ОС."""
    text = (
        "📖 **Документация по проекту Buff VPN**\n\n"
        "Наш VPN работает на базе протокола **VLESS-Reality** — это один из самых быстрых и скрытных "
        "протоколов шифрования на сегодняшний день. Он полностью маскирует трафик под обычное посещение зарубежных сайтов.\n\n"
        "Для начала работы выберите операционную систему вашего устройства, чтобы получить пошаговую инструкцию и ссылки на приложения:"
    )
    keyboard = [
        [InlineKeyboardButton(text="🍏 iOS (iPhone / iPad)", callback_data="inst_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="inst_android")],
        [InlineKeyboardButton(text="💻 Windows (ПК)", callback_data="inst_windows")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

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