import motor.motor_asyncio
from datetime import datetime
from bson import ObjectId
from PyToday import config

client = None
db = None

async def init_db():
    global client, db
    if not config.MONGODB_URI:
        raise ValueError("MONGODB_URI not set in environment variables")
    client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGODB_URI)
    db = client.telegram_adbot
    await db.users.create_index("_id")
    await db.bot_users.create_index("_id")
    await db.telegram_accounts.create_index("user_id")
    await db.account_stats.create_index("account_id")
    await db.message_logs.create_index([("user_id", 1), ("created_at", -1)])
    await db.target_groups.create_index([("user_id", 1)])
    await db.auto_reply_logs.create_index([("account_id", 1), ("created_at", -1)])
    await db.group_join_logs.create_index([("account_id", 1), ("created_at", -1)])

async def get_db():
    global db
    if db is None:
        await init_db()
    return db

async def save_bot_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    database = await get_db()
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

async def get_all_bot_users():
    database = await get_db()
    cursor = database.bot_users.find({})
    return await cursor.to_list(length=None)

async def get_bot_users_count():
    database = await get_db()
    return await database.bot_users.count_documents({})

async def get_user(user_id: int):
    database = await get_db()
    return await database.users.find_one({"_id": user_id})

async def create_user(user_id: int, username: str = None, first_name: str = None):
    database = await get_db()
    user = {
        "_id": user_id,
        "username": username,
        "first_name": first_name,
        "created_at": datetime.utcnow(),
        "ad_text": None,
        "time_interval": 60,
        "is_active": True,
        "use_multiple_accounts": False,
        "use_forward_mode": False,
        "auto_reply_enabled": False,
        "auto_reply_text": config.AUTO_REPLY_TEXT,
        "auto_group_join_enabled": False,
        "target_mode": "all",
        "selected_groups": []
    }
    await database.users.insert_one(user)
    return user

async def update_user(user_id: int, **kwargs):
    database = await get_db()
    await database.users.update_one({"_id": user_id}, {"$set": kwargs})

async def get_accounts(user_id: int, logged_in_only: bool = False):
    database = await get_db()
    query = {"user_id": user_id}
    if logged_in_only:
        query["is_logged_in"] = True
    cursor = database.telegram_accounts.find(query)
    return await cursor.to_list(length=None)

async def get_account(account_id) -> dict:
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    return await database.telegram_accounts.find_one({"_id": account_id})

async def create_account(user_id: int, phone: str, api_id: str, api_hash: str):
    database = await get_db()
    account = {
        "user_id": user_id,
        "phone": phone,
        "api_id": api_id,
        "api_hash": api_hash,
        "session_string": None,
        "is_logged_in": False,
        "created_at": datetime.utcnow(),
        "last_used": None,
        "phone_code_hash": None,
        "account_first_name": None,
        "account_last_name": None,
        "account_username": None
    }
    result = await database.telegram_accounts.insert_one(account)
    account["_id"] = result.inserted_id
    return account

async def update_account(account_id, **kwargs):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    await database.telegram_accounts.update_one({"_id": account_id}, {"$set": kwargs})

async def delete_account(account_id, user_id: int = None):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    query = {"_id": account_id}
    if user_id:
        query["user_id"] = user_id
    result = await database.telegram_accounts.delete_one(query)
    await database.account_stats.delete_many({"account_id": account_id})
    return result.deleted_count > 0

async def get_account_stats(account_id):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    return await database.account_stats.find_one({"account_id": account_id})

async def create_or_update_stats(account_id, **kwargs):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    stats = await get_account_stats(account_id)
    if stats:
        await database.account_stats.update_one({"account_id": account_id}, {"$set": kwargs})
    else:
        new_stats = {
            "account_id": account_id,
            "messages_sent": kwargs.get("messages_sent", 0),
            "messages_failed": kwargs.get("messages_failed", 0),
            "groups_count": kwargs.get("groups_count", 0),
            "marketplaces_count": kwargs.get("marketplaces_count", 0),
            "last_broadcast": kwargs.get("last_broadcast", None),
            "groups_joined": kwargs.get("groups_joined", 0),
            "auto_replies_sent": kwargs.get("auto_replies_sent", 0)
        }
        await database.account_stats.insert_one(new_stats)

async def increment_stats(account_id, field: str, amount: int = 1):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    stats = await get_account_stats(account_id)
    if stats:
        await database.account_stats.update_one({"account_id": account_id}, {"$inc": {field: amount}})
    else:
        await create_or_update_stats(account_id, **{field: amount})

async def create_message_log(user_id: int, account_id, chat_id: int, chat_title: str = None, status: str = "pending", error_message: str = None):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    log = {
        "user_id": user_id,
        "account_id": account_id,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "status": status,
        "error_message": error_message,
        "created_at": datetime.utcnow()
    }
    await database.message_logs.insert_one(log)
    return log

async def add_target_group(user_id: int, group_id: int, group_title: str = None):
    database = await get_db()
    existing = await database.target_groups.find_one({"user_id": user_id, "group_id": group_id})
    if not existing:
        await database.target_groups.insert_one({
            "user_id": user_id,
            "group_id": group_id,
            "group_title": group_title,
            "added_at": datetime.utcnow()
        })
        return True
    return False

async def remove_target_group(user_id: int, group_id: int):
    database = await get_db()
    result = await database.target_groups.delete_one({"user_id": user_id, "group_id": group_id})
    return result.deleted_count > 0

async def get_target_groups(user_id: int):
    database = await get_db()
    cursor = database.target_groups.find({"user_id": user_id})
    return await cursor.to_list(length=None)

async def clear_target_groups(user_id: int):
    database = await get_db()
    result = await database.target_groups.delete_many({"user_id": user_id})
    return result.deleted_count

async def log_auto_reply(account_id, from_user_id: int, from_username: str = None):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    await database.auto_reply_logs.insert_one({
        "account_id": account_id,
        "from_user_id": from_user_id,
        "from_username": from_username,
        "created_at": datetime.utcnow()
    })

async def log_group_join(account_id, group_id: int, group_title: str = None, invite_link: str = None):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    await database.group_join_logs.insert_one({
        "account_id": account_id,
        "group_id": group_id,
        "group_title": group_title,
        "invite_link": invite_link,
        "created_at": datetime.utcnow()
    })

async def get_auto_reply_count(account_id):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    return await database.auto_reply_logs.count_documents({"account_id": account_id})

async def get_groups_joined_count(account_id):
    database = await get_db()
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    return await database.group_join_logs.count_documents({"account_id": account_id})
