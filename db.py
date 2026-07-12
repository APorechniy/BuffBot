# db.py
import os
import aiosqlite
from datetime import datetime, timedelta

DB_NAME = os.getenv("DB_PATH", "database.db")

async def init_db():
    db_dir = os.path.dirname(DB_NAME)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                client_uuid TEXT UNIQUE,
                sub_id TEXT UNIQUE,
                status TEXT DEFAULT 'new',
                expires_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_or_get_user(user_id: int):
    user = await get_user(user_id)
    if not user:
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            await conn.commit()
        user = await get_user(user_id)
    return user

async def save_payment(order_id: str, user_id: int, amount: float):
    async with aiosqlite.connect(DB_NAME) as conn:
        now_str = datetime.now().isoformat()
        await conn.execute(
            "INSERT INTO payments (order_id, user_id, amount, created_at) VALUES (?, ?, ?, ?)",
            (order_id, user_id, amount, now_str)
        )
        await conn.commit()

async def get_payment(order_id: str):
    async with aiosqlite.connect(DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)) as cursor:
            return await cursor.fetchone()

async def mark_payment_success(order_id: str):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE payments SET status = 'success' WHERE order_id = ?", (order_id,))
        await conn.commit()

async def activate_user_subscription(user_id: int, client_uuid: str, sub_id: str, days: int = 30):
    async with aiosqlite.connect(DB_NAME) as conn:
        user = await get_user(user_id)
        current_expiry = None
        if user and user['expires_at'] and user['status'] == 'active':
            try:
                current_expiry = datetime.fromisoformat(user['expires_at'])
            except ValueError:
                pass
        
        base_time = current_expiry if (current_expiry and current_expiry > datetime.now()) else datetime.now()
        new_expiry = (base_time + timedelta(days=days)).isoformat()
        
        await conn.execute(
            """UPDATE users 
               SET client_uuid = ?, sub_id = ?, status = 'active', expires_at = ? 
               WHERE user_id = ?""",
            (client_uuid, sub_id, new_expiry, user_id)
        )
        await conn.commit()
        return new_expiry

async def update_user_status(user_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
        await conn.commit()

async def get_expired_users(now_str: str):
    async with aiosqlite.connect(DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM users WHERE status = 'active' AND expires_at <= ?", 
            (now_str,)
        ) as cursor:
            return await cursor.fetchall()

async def get_users_expiring_between(start_str: str, end_str: str):
    async with aiosqlite.connect(DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM users WHERE status = 'active' AND expires_at >= ? AND expires_at < ?",
            (start_str, end_str)
        ) as cursor:
            return await cursor.fetchall()