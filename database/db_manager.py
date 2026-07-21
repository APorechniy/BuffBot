# database/db_manager.py
import os
import aiosqlite
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

DB_NAME = os.getenv("DB_PATH", "data/database.db")

@asynccontextmanager
async def get_db_connection():
    """Асинхронный контекстный менеджер для подключения к БД c WAL-режимом."""
    async with aiosqlite.connect(DB_NAME, timeout=15.0) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA busy_timeout=5000;")
        yield conn

async def init_db():
    db_dir = os.path.dirname(DB_NAME)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    async with get_db_connection() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                client_uuid TEXT UNIQUE,
                sub_id TEXT UNIQUE,
                status TEXT DEFAULT 'new',
                expires_at TEXT,
                trial_used INTEGER DEFAULT 0,
                warned_1d INTEGER DEFAULT 0,
                warned_3d INTEGER DEFAULT 0
            )
        """)
        # Авто-миграции для существующих БД
        try:
            await db.execute("ALTER TABLE users ADD COLUMN warned_1d INTEGER DEFAULT 0;")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN warned_3d INTEGER DEFAULT 0;")
        except Exception:
            pass

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
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_or_get_user(user_id: int):
    user = await get_user(user_id)
    if not user:
        async with get_db_connection() as conn:
            await conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            await conn.commit()
        user = await get_user(user_id)
    return user

async def save_payment(order_id: str, user_id: int, amount: float):
    async with get_db_connection() as conn:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await conn.execute(
            "INSERT INTO payments (order_id, user_id, amount, created_at) VALUES (?, ?, ?, ?)",
            (order_id, user_id, amount, now_str)
        )
        await conn.commit()

async def get_payment(order_id: str):
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)) as cursor:
            return await cursor.fetchone()

async def mark_payment_success(order_id: str):
    async with get_db_connection() as conn:
        await conn.execute("UPDATE payments SET status = 'success' WHERE order_id = ?", (order_id,))
        await conn.commit()

async def activate_user_subscription(user_id: int, client_uuid: str, sub_id: str, days: int):
    async with get_db_connection() as conn:
        user = await get_user(user_id)
        current_expiry = None
        if user and user['expires_at'] and user['status'] == 'active':
            try:
                current_expiry = datetime.strptime(user['expires_at'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        base_time = current_expiry if (current_expiry and current_expiry > datetime.now()) else datetime.now()
        new_expiry = (base_time + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        await conn.execute(
            """UPDATE users 
               SET client_uuid = ?, sub_id = ?, status = 'active', expires_at = ?,
                   warned_1d = 0, warned_3d = 0 
               WHERE user_id = ?""",
            (client_uuid, sub_id, new_expiry, user_id)
        )
        await conn.commit()
        return new_expiry

async def use_trial_db(user_id: int, client_uuid: str, sub_id: str, expires_at_str: str):
    async with get_db_connection() as conn:
        await conn.execute(
            """UPDATE users 
               SET client_uuid = ?, sub_id = ?, status = 'active', expires_at = ?, trial_used = 1,
                   warned_1d = 0, warned_3d = 0 
               WHERE user_id = ?""",
            (client_uuid, sub_id, expires_at_str, user_id)
        )
        await conn.commit()

async def update_user_status(user_id: int, status: str):
    async with get_db_connection() as conn:
        await conn.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
        await conn.commit()

async def get_expired_users(now_str: str):
    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT * FROM users WHERE status = 'active' AND expires_at <= ?", 
            (now_str,)
        ) as cursor:
            return await cursor.fetchall()

async def get_users_for_warning(expires_before_str: str, warning_type: str):
    col = "warned_1d" if warning_type == "1d" else "warned_3d"
    async with get_db_connection() as conn:
        async with conn.execute(
            f"SELECT * FROM users WHERE status = 'active' AND {col} = 0 AND expires_at <= ?",
            (expires_before_str,)
        ) as cursor:
            return await cursor.fetchall()

async def mark_user_warned(user_id: int, warning_type: str):
    col = "warned_1d" if warning_type == "1d" else "warned_3d"
    async with get_db_connection() as conn:
        await conn.execute(f"UPDATE users SET {col} = 1 WHERE user_id = ?", (user_id,))
        await conn.commit()