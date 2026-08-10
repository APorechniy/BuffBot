import pytest_asyncio
from datetime import datetime

from database.db_manager import (
    init_db, 
    get_user, 
    create_or_get_user, 
    save_payment, 
    get_payment, 
    mark_payment_success,
    activate_user_subscription,
    delete_all_temp_users,
    DB_NAME
)

# Инициализация тестовой БД и подмена пути
@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(tmp_path, monkeypatch):
    test_db_path = str(tmp_path / "test_database.db")
    
    monkeypatch.setattr("database.db_manager.DB_NAME", test_db_path)
    
    await init_db()
    
    yield

async def test_create_and_get_user():
    """Тест создания пользователя и его получения из БД."""
    user_id = 12345678
    
    user = await get_user(user_id)
    assert user is None
    
    created_user = await create_or_get_user(user_id=user_id, sub_id="sub_123")
    assert created_user is not None
    assert created_user["user_id"] == user_id
    assert created_user["sub_id"] == "sub_123"
    assert created_user["status"] == "new"

    user_again = await create_or_get_user(user_id=user_id)
    assert user_again["user_id"] == user_id

async def test_payment_lifecycle():
    """Тест полного цикла оплаты: сохранение -> получение -> успешный статус."""
    order_id = "PAY-999"
    user_id = 777
    amount = 150.50
    tariff_id = "150"
    
    # 1. Сохраняем платеж
    await save_payment(order_id, user_id, amount, tariff_id)
    
    # 2. Достаем платеж и проверяем поля
    payment = await get_payment(order_id)
    assert payment is not None
    assert payment["order_id"] == order_id
    assert payment["amount"] == 150.50
    assert payment["status"] == "pending" # Статус по умолчанию
    assert payment["tariff_id"] == "150"
    
    # 3. Отмечаем платеж как успешный
    await mark_payment_success(order_id)
    
    # 4. Проверяем, что статус изменился на success
    updated_payment = await get_payment(order_id)
    assert updated_payment["status"] == "success"

async def test_activate_subscription():
    """Тест продления подписки пользователю."""
    user_id = 111
    await create_or_get_user(user_id)
    
    # Активируем подписку на 1 день и 2 часа
    new_expiry = await activate_user_subscription(
        user_id=user_id, 
        client_uuid="uuid-abc", 
        sub_id="sub-abc", 
        days=1, 
        hours=2
    )
    
    # Достаем юзера и проверяем обновления
    user = await get_user(user_id)
    assert user["status"] == "active"
    assert user["client_uuid"] == "uuid-abc"
    assert user["expires_at"] == new_expiry

async def test_delete_temp_users():
    """Тест удаления временных (temp_) пользователей, у которых истек срок."""
    # Создаем юзера с 'temp_' в sub_id
    user_id = 999
    await create_or_get_user(user_id, sub_id="temp_123")
    
    # Помечаем его истекшим (дата в прошлом)
    await activate_user_subscription(user_id, "uuid", "temp_123", days=-10)
    
    # Запускаем очистку для текущего времени
    now_str = datetime.now().isoformat()
    deleted_users = await delete_all_temp_users(now_str)
    
    # Проверяем, что удаленный пользователь вернулся в списке
    assert len(deleted_users) == 1
    assert deleted_users[0]["user_id"] == user_id
    
    # Проверяем, что его больше нет в БД
    user = await get_user(user_id)
    assert user is None