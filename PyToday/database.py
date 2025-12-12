import motor.motor_asyncio
import aiosqlite
from datetime import datetime
from bson import ObjectId
from PyToday import *
import asyncio
import logging

logger = logging.getLogger(__name__)

mongo_client = None
mongo_db = None
sqlite_db_path = config.SQLITE_DB_PATH

async def init_db():
    global mongo_client, mongo_db
    
    if config.MONGODB_URI:
        try:
            mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=config.CONNECTION_POOL_SIZE,
                retryWrites=True
            )
            mongo_db = mongo_client.telegram_adbot
            await mongo_db.bot_users.create_index("_id")
            logger.info("MongoDB connected successfully")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
    
    async with aiosqlite.connect(sqlite_db_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT,
                ad_text TEXT,
                time_interval INTEGER DEFAULT 60,
                is_active INTEGER DEFAULT 1,
                use_multiple_accounts INTEGER DEFAULT 0,
                use_forward_mode INTEGER DEFAULT 0,
                auto_reply_enabled INTEGER DEFAULT 0,
                auto_reply_text TEXT,
                auto_group_join_enabled INTEGER DEFAULT 0,
                target_mode TEXT DEFAULT 'all',
                selected_groups TEXT DEFAULT '[]',
                saved_message_id INTEGER,
                selected_accounts TEXT DEFAULT '[]',
                selected_single_account TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS telegram_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                phone TEXT,
                api_id TEXT,
                api_hash TEXT,
                session_string TEXT,
                is_logged_in INTEGER DEFAULT 0,
                created_at TEXT,
                last_used TEXT,
                phone_code_hash TEXT,
                account_first_name TEXT,
                account_last_name TEXT,
                account_username TEXT,
                saved_message_id INTEGER
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS account_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                messages_sent INTEGER DEFAULT 0,
                messages_failed INTEGER DEFAULT 0,
                groups_count INTEGER DEFAULT 0,
                marketplaces_count INTEGER DEFAULT 0,
                last_broadcast TEXT,
                groups_joined INTEGER DEFAULT 0,
                auto_replies_sent INTEGER DEFAULT 0
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS target_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                group_id INTEGER,
                group_title TEXT,
                added_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS auto_reply_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                from_user_id INTEGER,
                from_username TEXT,
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS group_join_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                group_id INTEGER,
                group_title TEXT,
                invite_link TEXT,
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS dm_replied_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                user_id INTEGER,
                username TEXT,
                replied_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                chat_id INTEGER,
                chat_title TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS force_sub (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                channel_link TEXT,
                group_id TEXT,
                group_link TEXT,
                enabled INTEGER DEFAULT 0
            )
        ''')
        
        existing = await db.execute("SELECT * FROM force_sub WHERE id = 1")
        if not await existing.fetchone():
            await db.execute("INSERT INTO force_sub (id, enabled) VALUES (1, 0)")
        
        await db.commit()
        logger.info("SQLite database initialized successfully")

async def get_mongo_db():
    global mongo_db
    if mongo_db is None:
        await init_db()
    return mongo_db

async def save_bot_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    database = await get_mongo_db()
    if database is not None:
        try:
            existing = await database.bot_users.find_one({"_id": user_id})
            if existing:
                await database.bot_users.update_one(
                    {"_id": user_id},
                    {"$set": {
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "last_seen": datetime.utcnow()
                    }}
                )
            else:
                await database.bot_users.insert_one({
                    "_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "created_at": datetime.utcnow(),
                    "last_seen": datetime.utcnow()
                })
        except Exception as e:
            logger.error(f"Error saving bot user to MongoDB: {e}")

async def get_all_bot_users():
    database = await get_mongo_db()
    if database is not None:
        try:
            cursor = database.bot_users.find({})
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error getting bot users: {e}")
            return []
    return []

async def get_bot_users_count():
    database = await get_mongo_db()
    if database is not None:
        try:
            return await database.bot_users.count_documents({})
        except Exception as e:
            logger.error(f"Error counting bot users: {e}")
            return 0
    return 0

async def get_user(user_id: int):
    async with aiosqlite.connect(sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

async def create_user(user_id: int, username: str = None, first_name: str = None):
    async with aiosqlite.connect(sqlite_db_path) as db:
        await db.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, created_at, auto_reply_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.utcnow().isoformat(), config.AUTO_REPLY_TEXT))
        await db.commit()
    return await get_user(user_id)

async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    async with aiosqlite.connect(sqlite_db_path) as db:
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        await db.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
        await db.commit()

async def get_accounts(user_id: int, logged_in_only: bool = False):
    async with aiosqlite.connect(sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM telegram_accounts WHERE user_id = ?"
        if logged_in_only:
            query += " AND is_logged_in = 1"
        cursor = await db.execute(query, (user_id,))
        rows = await cursor.fetchall()
        return [{"_id": row["id"], **dict(row)} for row in rows]

async def get_account(account_id) -> dict:
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM telegram_accounts WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        if row:
            return {"_id": row["id"], **dict(row)}
        return None

async def create_account(user_id: int, phone: str, api_id: str, api_hash: str):
    async with aiosqlite.connect(sqlite_db_path) as db:
        cursor = await db.execute('''
            INSERT INTO telegram_accounts (user_id, phone, api_id, api_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, phone, api_id, api_hash, datetime.utcnow().isoformat()))
        await db.commit()
        account_id = cursor.lastrowid
        return await get_account(account_id)

async def update_account(account_id, **kwargs):
    if isinstance(account_id, str):
        account_id = int(account_id)
    if not kwargs:
        return
    async with aiosqlite.connect(sqlite_db_path) as db:
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [account_id]
        await db.execute(f"UPDATE telegram_accounts SET {set_clause} WHERE id = ?", values)
        await db.commit()

async def delete_account(account_id, user_id: int = None):
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        query = "DELETE FROM telegram_accounts WHERE id = ?"
        params = [account_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        cursor = await db.execute(query, params)
        await db.execute("DELETE FROM account_stats WHERE account_id = ?", (account_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_account_stats(account_id):
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM account_stats WHERE account_id = ?", (account_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

async def create_or_update_stats(account_id, **kwargs):
    if isinstance(account_id, str):
        account_id = int(account_id)
    stats = await get_account_stats(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        if stats:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [account_id]
            await db.execute(f"UPDATE account_stats SET {set_clause} WHERE account_id = ?", values)
        else:
            await db.execute('''
                INSERT INTO account_stats (account_id, messages_sent, messages_failed, groups_count, marketplaces_count, groups_joined, auto_replies_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                account_id,
                kwargs.get("messages_sent", 0),
                kwargs.get("messages_failed", 0),
                kwargs.get("groups_count", 0),
                kwargs.get("marketplaces_count", 0),
                kwargs.get("groups_joined", 0),
                kwargs.get("auto_replies_sent", 0)
            ))
        await db.commit()

async def increment_stats(account_id, field: str, amount: int = 1):
    if isinstance(account_id, str):
        account_id = int(account_id)
    stats = await get_account_stats(account_id)
    if stats:
        async with aiosqlite.connect(sqlite_db_path) as db:
            await db.execute(f"UPDATE account_stats SET {field} = {field} + ? WHERE account_id = ?", (amount, account_id))
            await db.commit()
    else:
        await create_or_update_stats(account_id, **{field: amount})

async def create_message_log(user_id: int, account_id, chat_id: int, chat_title: str = None, status: str = "pending", error_message: str = None):
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        await db.execute('''
            INSERT INTO message_logs (user_id, account_id, chat_id, chat_title, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, account_id, chat_id, chat_title, status, error_message, datetime.utcnow().isoformat()))
        await db.commit()

async def add_target_group(user_id: int, group_id: int, group_title: str = None):
    async with aiosqlite.connect(sqlite_db_path) as db:
        cursor = await db.execute("SELECT * FROM target_groups WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        if not await cursor.fetchone():
            await db.execute('''
                INSERT INTO target_groups (user_id, group_id, group_title, added_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, group_id, group_title, datetime.utcnow().isoformat()))
            await db.commit()
            return True
        return False

async def remove_target_group(user_id: int, group_id: int):
    async with aiosqlite.connect(sqlite_db_path) as db:
        cursor = await db.execute("DELETE FROM target_groups WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_target_groups(user_id: int):
    async with aiosqlite.connect(sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM target_groups WHERE user_id = ?", (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def clear_target_groups(user_id: int):
    async with aiosqlite.connect(sqlite_db_path) as db:
        cursor = await db.execute("DELETE FROM target_groups WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount

async def log_auto_reply(account_id, from_user_id: int, from_username: str = None):
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        await db.execute('''
            INSERT INTO auto_reply_logs (account_id, from_user_id, from_username, created_at)
            VALUES (?, ?, ?, ?)
        ''', (account_id, from_user_id, from_username, datetime.utcnow().isoformat()))
        await db.commit()

async def log_group_join(account_id, group_id: int, group_title: str = None, invite_link: str = None):
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        await db.execute('''
            INSERT INTO group_join_logs (account_id, group_id, group_title, invite_link, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (account_id, group_id, group_title, invite_link, datetime.utcnow().isoformat()))
        await db.commit()

async def get_auto_reply_count(account_id):
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM auto_reply_logs WHERE account_id = ?", (account_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_groups_joined_count(account_id):
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM group_join_logs WHERE account_id = ?", (account_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def has_replied_to_user(account_id, user_id: int) -> bool:
    if isinstance(account_id, str):
        account_id = int(account_id)
    async with aiosqlite.connect(sqlite_db_path) as db:
        cursor = await db.execute("SELECT * FROM dm_replied_users WHERE account_id = ? AND user_id = ?", (account_id, user_id))
        return await cursor.fetchone() is not None

async def mark_user_replied(account_id, user_id: int, username: str = None):
    if isinstance(account_id, str):
        account_id = int(account_id)
    if not await has_replied_to_user(account_id, user_id):
        async with aiosqlite.connect(sqlite_db_path) as db:
            await db.execute('''
                INSERT INTO dm_replied_users (account_id, user_id, username, replied_at)
                VALUES (?, ?, ?, ?)
            ''', (account_id, user_id, username, datetime.utcnow().isoformat()))
            await db.commit()
            return True
    return False

async def get_force_sub_settings():
    async with aiosqlite.connect(sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM force_sub WHERE id = 1")
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return {"enabled": 0, "channel_id": None, "channel_link": None, "group_id": None, "group_link": None}

async def update_force_sub_settings(**kwargs):
    async with aiosqlite.connect(sqlite_db_path) as db:
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        await db.execute(f"UPDATE force_sub SET {set_clause} WHERE id = 1", values)
        await db.commit()

async def toggle_force_sub():
    settings = await get_force_sub_settings()
    new_status = 0 if settings.get("enabled") else 1
    await update_force_sub_settings(enabled=new_status)
    return new_status == 1
