import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot

from utils.helpers import (
    load_tariffs,
    verify_internal_token,
    grant_vpn_access,
    activate_trial_period,
    create_temp_user
)

# -------------------------------------------------------------------
# 1. ТЕСТ ЗАГРУЗКИ ТАРИФОВ ИЗ JSON
# -------------------------------------------------------------------

def test_load_tariffs(tmp_path):
    """Тестируем чтение файла tariffs.json."""
    # Создаем временный файл JSON
    tariffs_data = {
        "1_month": {"price": 100, "days": 30, "name": "Тест"},
        "3_month": {"price": 250, "days": 90, "name": "Тест 3 месяца"}
    }
    json_file = tmp_path / "test_tariffs.json"
    json_file.write_text(json.dumps(tariffs_data, ensure_ascii=False), encoding="utf-8")

    # Читаем тарифы нашей функцией
    result = load_tariffs(str(json_file))

    # Проверяем совпадение
    assert result == tariffs_data
    assert "1_month" in result
    assert result["1_month"]["price"] == 100


# -------------------------------------------------------------------
# 2. ТЕСТ ПРОВЕРКИ СЕКРЕТНОГО ТОКЕНА (BEARER / INTERNAL SECRET)
# -------------------------------------------------------------------

def test_verify_internal_token():
    """Тестируем функцию сверки токенов (защита от несанкционированного доступа)."""
    with patch("utils.helpers.settings.INTERNAL_API_SECRET", "super_secret_key_123"):
        # Верный токен
        assert verify_internal_token("super_secret_key_123") is True
        
        # Неверный токен
        assert verify_internal_token("wrong_key") is False
        
        # Пустой токен или None
        assert verify_internal_token("") is False
        assert verify_internal_token(None) is False


# -------------------------------------------------------------------
# 3. ТЕСТ ВЫДАЧИ VPN-ДОСТУПА (grant_vpn_access)
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grant_vpn_access_success():
    """Тест успешной выдачи VPN подписки (когда 3X-UI панель ответила УСПЕШНО)."""
    user_id = 777
    
    fake_user = {
        "user_id": user_id,
        "client_uuid": "old-uuid-123",
        "sub_id": "old-sub-123",
        "status": "new",
        "expires_at": None
    }

    # Мокируем X3UiClient
    mock_xui_instance = AsyncMock()
    mock_xui_instance.add_client.return_value = True  # add_client вернул True (успех)

    with patch("utils.helpers.db.get_user", AsyncMock(return_value=fake_user)), \
         patch("utils.helpers.db.activate_user_subscription", AsyncMock()) as mock_db_activate, \
         patch("utils.helpers.X3UiClient", return_value=mock_xui_instance):

        # Вызываем функцию
        sub_link = await grant_vpn_access(user_id=user_id, days=30)

        # 1. Проверяем, что ссылка сформирована верно
        assert "buff-subscribe/old-sub-123" in sub_link
        
        # 2. Проверяем, что метод add_client был вызван у панели 3X-UI
        mock_xui_instance.add_client.assert_called_once()
        
        # 3. Проверяем, что в локальную БД была записана информация про подписку
        mock_db_activate.assert_called_once_with(
            user_id, "old-uuid-123", "old-sub-123", days=30, hours=0, minutes=0
        )


@pytest.mark.asyncio
async def test_grant_vpn_access_3xui_error_raises_exception():
    """Тест сценария, когда 3X-UI панель отклонила и создание, и обновление клиента."""
    user_id = 777
    fake_user = {"user_id": user_id, "client_uuid": None, "sub_id": None, "status": "new", "expires_at": None}

    # Мокируем X3UiClient так, чтобы ВСЕ попытки вызова вернули False (ошибка панели)
    mock_xui_instance = AsyncMock()
    mock_xui_instance.add_client.return_value = False
    mock_xui_instance.update_client_status.return_value = False

    with patch("utils.helpers.db.get_user", AsyncMock(return_value=fake_user)), \
         patch("utils.helpers.X3UiClient", return_value=mock_xui_instance):

        # Ожидаем, что функция выбросит Exception
        with pytest.raises(Exception) as exc_info:
            await grant_vpn_access(user_id=user_id, days=30)

        assert "3X-UI панели отклонила обновление параметров клиента" in str(exc_info.value)


# -------------------------------------------------------------------
# 4. ТЕСТ АКТИВАЦИИ ПРОБНОГО ПЕРИОДА (activate_trial_period)
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_activate_trial_already_used():
    """Тест: пользователь пытается снова взять триал, хотя уже использовал его."""
    user_id = 888
    fake_user = {"user_id": user_id, "trial_used": 1} # Триал уже был использован
    mock_bot = AsyncMock(spec=Bot)

    with patch("utils.helpers.db.create_or_get_user", AsyncMock(return_value=fake_user)):
        success, message = await activate_trial_period(user_id, mock_bot)

        # Должен вернуться отказ
        assert success is False
        assert "Вы уже использовали ваш пробный период ранее" in message
        
        # Бот НЕ должен был отправлять никаких сообщений
        mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_activate_trial_success():
    """Тест успешной активации первого пробного периода."""
    user_id = 999
    fake_user = {"user_id": user_id, "trial_used": 0, "client_uuid": None, "sub_id": "trial_sub"}
    mock_bot = AsyncMock(spec=Bot)

    mock_xui_instance = AsyncMock()
    mock_xui_instance.add_client.return_value = True

    with patch("utils.helpers.db.create_or_get_user", AsyncMock(return_value=fake_user)), \
         patch("utils.helpers.db.use_trial_db", AsyncMock()) as mock_use_trial, \
         patch("utils.helpers.X3UiClient", return_value=mock_xui_instance):

        success, sub_link = await activate_trial_period(user_id, mock_bot)

        assert success is True
        assert "buff-subscribe/trial_sub" in sub_link

        # Проверяем, что в БД зафиксировано использование триала
        mock_use_trial.assert_called_once()
        
        # Проверяем, что бот отправил поздравление пользователю
        mock_bot.send_message.assert_called_once()
        assert "активирован бесплатный пробный период" in mock_bot.send_message.call_args[0][1]


# -------------------------------------------------------------------
# 5. ТЕСТ СОЗДАНИЯ ВРЕМЕННОГО ДЕМО-ПОЛЬЗОВАТЕЛЯ (create_temp_user)
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_temp_user_success():
    """Тест успешного создания временного пользователя (temp_...)."""
    mock_bot = AsyncMock(spec=Bot)
    mock_xui_instance = AsyncMock()
    mock_xui_instance.add_client.return_value = True

    with patch("utils.helpers.X3UiClient", return_value=mock_xui_instance), \
         patch("utils.helpers.db.create_or_get_user", AsyncMock()) as mock_db_create:

        success, sub_link = await create_temp_user(mock_bot)

        assert success is True
        assert "buff-subscribe/temp_" in sub_link
        mock_db_create.assert_called_once()