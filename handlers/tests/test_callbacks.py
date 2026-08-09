import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import CallbackQuery, Message, User
from aiogram import Bot

# Импортируем тестируемые хэндлеры
from handlers.callbacks import (
    process_show_docs,
    process_show_inst,
    process_show_terms,
    process_buy_tariff
)

# -------------------------------------------------------------------
# Вспомогательные фикстуры для создания фейковых объектов Aiogram
# -------------------------------------------------------------------

@pytest.fixture
def mock_user():
    """Создает фейкового пользователя Telegram."""
    user = MagicMock(spec=User)
    user.id = 123456789
    user.username = "test_user"
    user.first_name = "Test"
    return user

@pytest.fixture
def mock_callback_query(mock_user):
    """Создает фейковый CallbackQuery с вложенным фейковым Сообщением."""
    # 1. Создаем фейковое сообщение, у которого метод edit_text асинхронный
    message_mock = MagicMock(spec=Message)
    message_mock.edit_text = AsyncMock()

    # 2. Создаем сам CallbackQuery
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = mock_user
    callback.message = message_mock
    callback.data = "show_docs" # data по умолчанию
    callback.answer = AsyncMock() # метод answer() тоже асинхронный

    return callback


# -------------------------------------------------------------------
# ТЕСТЫ ХЭНДЛЕРОВ
# -------------------------------------------------------------------
async def test_process_show_docs(mock_callback_query):
    """Тестируем хэндлер открытия главного меню документации."""
    
    # 1. Вызываем наш хэндлер
    await process_show_docs(mock_callback_query)

    # 2. Проверяем, что хэндлер отредактировал сообщение
    mock_callback_query.message.edit_text.assert_called_once()
    
    # 3. Проверяем, что в отредактированном тексте есть ключевая фраза
    call_args = mock_callback_query.message.edit_text.call_args
    edited_text = call_args[0][0] # Первый аргумент вызова edit_text — это текст
    
    assert "Документация по проекту Buff VPN" in edited_text
    assert "Шифрование трафика" in edited_text
    assert "Инструкции по настройке:" in edited_text

@pytest.mark.parametrize("platform, expected_keyword", [
    ("inst_ios", "iOS (iPhone / iPad)"),
    ("inst_android", "v2rayNG"),
    ("inst_windows", "Windows")
])
async def test_process_show_inst_platforms(mock_callback_query, platform, expected_keyword):
    """
    Параметризованный тест: проверяет сразу 3 ОС (iOS, Android, Windows).
    pytest автоматически запустит этот тест 3 раза с разными аргументами!
    """
    # Задаем callback_data для конкретной платформы
    mock_callback_query.data = platform

    # Запускаем хэндлер
    await process_show_inst(mock_callback_query)

    # Проверяем, что редактирование текста и всплывашка (answer) были вызваны
    mock_callback_query.message.edit_text.assert_called_once()
    mock_callback_query.answer.assert_called_once()

    # Проверяем, что в ответе содержится правильная инструкция
    edited_text = mock_callback_query.message.edit_text.call_args[0][0]
    assert expected_keyword in edited_text

async def test_process_show_terms(mock_callback_query):
    """Тестируем показ политики конфиденциальности."""
    await process_show_terms(mock_callback_query)

    # Проверяем, что вызван ответ на коллбэк (чтобы убрать часики на кнопке в Telegram)
    mock_callback_query.answer.assert_called_once()
    
    edited_text = mock_callback_query.message.edit_text.call_args[0][0]
    assert "Политика конфиденциальности" in edited_text

async def test_process_buy_tariff_not_found(mock_callback_query):
    """
    Тестируем сценарий, когда пользователь пытался купить тариф, 
    которого больше нет в конфиге/БД.
    """
    mock_callback_query.data = "buy:unknown_tariff_code"
    mock_bot = AsyncMock(spec=Bot)

    # Перехватываем (patch) функцию load_tariffs, чтобы она вернула пустой словарь
    with patch("utils.helpers.load_tariffs", return_value={}):
        await process_buy_tariff(mock_callback_query, bot=mock_bot)

    # Бот должен показать всплывашку (show_alert) с ошибкой "не найден"
    mock_callback_query.answer.assert_called_once_with(
        "❌ Выбранный тариф не найден или устарел.", 
        show_alert=True
    )