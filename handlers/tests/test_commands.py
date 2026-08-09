import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User

from handlers.commands import cmd_start, cmd_privacy, cmd_terms

# -------------------------------------------------------------------
# Вспомогательная фикстура фейкового сообщения от пользователя
# -------------------------------------------------------------------
@pytest.fixture
def mock_message():
    """Создает фейковое сообщение от пользователя (например, команда /start)."""
    user = MagicMock(spec=User)
    user.id = 55555
    user.first_name = "Alex"

    message = MagicMock(spec=Message)
    message.from_user = user
    message.answer = AsyncMock()  # Подделываем ответ бота
    return message


# -------------------------------------------------------------------
# ТЕСТЫ КОМАНДЫ /start
# -------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cmd_start_new_user_trial_available(mock_message):
    """Сценарий 1: /start от нового пользователя (триал еще НЕ использован)."""
    
    # Фейковые данные, которые "вернет" наша база данных
    fake_db_user = {
        'status': 'new',
        'expires_at': None,
        'sub_id': '55555',
        'trial_used': 0  # Триал еще не брал
    }

    # Подменяем обращение к БД
    with patch("handlers.commands.db.create_or_get_user", AsyncMock(return_value=fake_db_user)):
        await cmd_start(mock_message)

    # Проверяем, что бот ответил на сообщение
    mock_message.answer.assert_called_once()
    
    # Извлекаем отправленный текст и клавиатуру
    args, kwargs = mock_message.answer.call_args
    sent_text = args[0]
    reply_markup = kwargs.get("reply_markup")

    # 1. Проверяем текст
    assert "❌ **Статус:** Доступ отсутствует." in sent_text
    assert "🎁 Вам доступен бесплатный тест на 1 день!" in sent_text

    # 2. Проверяем, что кнопка "activate_trial" есть в клавиатуре
    inline_keyboard = reply_markup.inline_keyboard
    callbacks_in_keyboard = [btn.callback_data for row in inline_keyboard for btn in row]
    assert "activate_trial" in callbacks_in_keyboard

@pytest.mark.asyncio
async def test_cmd_start_trial_already_used(mock_message):
    """Сценарий 2: /start от пользователя, который УЖЕ использовал триал."""
    
    fake_db_user = {
        'status': 'expired',
        'expires_at': '2024-01-01T10:00:00',
        'sub_id': '55555',
        'trial_used': 1  # Триал УЖЕ использован
    }

    with patch("handlers.commands.db.create_or_get_user", AsyncMock(return_value=fake_db_user)):
        await cmd_start(mock_message)

    args, kwargs = mock_message.answer.call_args
    sent_text = args[0]
    reply_markup = kwargs.get("reply_markup")

    # Проверяем, что текста и кнопки про триал НЕТ
    assert "❌ **Статус:** Доступ отсутствует." in sent_text
    assert "🎁 Вам доступен бесплатный тест" not in sent_text

    callbacks_in_keyboard = [btn.callback_data for row in reply_markup.inline_keyboard for btn in row]
    assert "activate_trial" not in callbacks_in_keyboard


@pytest.mark.asyncio
async def test_cmd_start_active_user(mock_message):
    """Сценарий 3: /start от пользователя с АКТИВНОЙ подпиской."""
    
    fake_db_user = {
        'status': 'active',
        'expires_at': '2026-12-31T23:59:00',
        'sub_id': 'user_sub_123',
        'trial_used': 1
    }

    with patch("handlers.commands.db.create_or_get_user", AsyncMock(return_value=fake_db_user)):
        await cmd_start(mock_message)

    args, kwargs = mock_message.answer.call_args
    sent_text = args[0]
    reply_markup = kwargs.get("reply_markup")

    # Проверяем наличие активного статуса и сгенерированной ссылки
    assert "✅ **Статус:** Активен" in sent_text
    assert "buff-subscribe/user_sub_123" in sent_text

    # Проверяем, что появилось меню активного юзера (кнопка Инструкции)
    callbacks_in_keyboard = [btn.callback_data for row in reply_markup.inline_keyboard for btn in row]
    assert "show_instructions" in callbacks_in_keyboard


# -------------------------------------------------------------------
# ТЕСТЫ ПРОСТЫХ КОМАНД (/privacy, /terms)
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cmd_privacy(mock_message):
    """Тест команды /privacy."""
    await cmd_privacy(mock_message)
    mock_message.answer.assert_called_once()
    
    sent_text = mock_message.answer.call_args[0][0]
    assert "Политика конфиденциальности" in sent_text


@pytest.mark.asyncio
async def test_cmd_terms(mock_message):
    """Тест команды /terms."""
    await cmd_terms(mock_message)
    mock_message.answer.assert_called_once()
    
    sent_text = mock_message.answer.call_args[0][0]
    assert "Пользовательское соглашение" in sent_text