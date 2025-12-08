import asyncio
import logging
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.messages import ForwardMessagesRequest, ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel, Chat, InputPeerChannel, InputPeerSelf
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, PasswordHashInvalidError, UserAlreadyParticipantError, InviteHashExpiredError, InviteHashInvalidError
from datetime import datetime
from bson import ObjectId
from PyToday import database
from PyToday.encryption import encrypt_data, decrypt_data
from PyToday import config

logger = logging.getLogger(__name__)
active_clients = {}

async def create_client(api_id, api_hash, session_string=None):
    if session_string:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
    else:
        client = TelegramClient(StringSession(), api_id, api_hash)
    return client

async def send_code(api_id, api_hash, phone):
    client = await create_client(api_id, api_hash)
    await client.connect()
    
    try:
        result = await client.send_code_request(phone)
        session_string = client.session.save()
        await client.disconnect()
        return {
            "success": True,
            "phone_code_hash": result.phone_code_hash,
            "session_string": session_string
        }
    except Exception as e:
        await client.disconnect()
        return {"success": False, "error": str(e)}

async def verify_code(api_id, api_hash, phone, code, phone_code_hash, session_string):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        new_session = client.session.save()
        await client.disconnect()
        return {"success": True, "session_string": new_session}
    except PhoneCodeInvalidError:
        await client.disconnect()
        return {"success": False, "error": "Invalid OTP code. Please try again."}
    except PhoneCodeExpiredError:
        await client.disconnect()
        return {"success": False, "error": "OTP code expired. Please request a new code."}
    except SessionPasswordNeededError:
        temp_session = client.session.save()
        await client.disconnect()
        return {
            "success": False, 
            "error": "2FA_REQUIRED",
            "requires_2fa": True,
            "session_string": temp_session
        }
    except Exception as e:
        await client.disconnect()
        return {"success": False, "error": str(e)}

async def verify_2fa_password(api_id, api_hash, password, session_string):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    
    try:
        await client.sign_in(password=password)
        new_session = client.session.save()
        
        if config.ACCOUNT_NAME_SUFFIX or config.ACCOUNT_BIO_TEMPLATE:
            try:
                me = await client.get_me()
                current_name = me.first_name or ""
                new_first_name = current_name
                if config.ACCOUNT_NAME_SUFFIX and config.ACCOUNT_NAME_SUFFIX not in current_name:
                    new_first_name = f"{current_name} {config.ACCOUNT_NAME_SUFFIX}"
                
                await client(UpdateProfileRequest(
                    first_name=new_first_name,
                    about=config.ACCOUNT_BIO_TEMPLATE
                ))
                new_session = client.session.save()
            except Exception as e:
                logger.warning(f"Failed to update profile after 2FA: {e}")
        
        await client.disconnect()
        return {"success": True, "session_string": new_session}
    except PasswordHashInvalidError:
        await client.disconnect()
        return {"success": False, "error": "Invalid 2FA password. Please try again."}
    except Exception as e:
        await client.disconnect()
        return {"success": False, "error": str(e)}

async def get_groups_and_marketplaces(account_id):
    try:
        if isinstance(account_id, str):
            account_id = ObjectId(account_id)
        account = await database.get_account(account_id)
        if not account or not account.get('is_logged_in'):
            return {"success": False, "error": "Account not logged in"}
        
        api_id = decrypt_data(account.get('api_id', ''))
        api_hash = decrypt_data(account.get('api_hash', ''))
        session_string = decrypt_data(account.get('session_string', ''))
        
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Session expired. Please login again."}
        
        groups = []
        marketplaces = []
        
        dialogs = await client.get_dialogs(limit=500)
        
        for dialog in dialogs:
            entity = dialog.entity
            
            if isinstance(entity, Channel):
                if entity.broadcast:
                    continue
                if not entity.megagroup:
                    continue
            
            if isinstance(entity, (Channel, Chat)):
                is_marketplace = False
                title = dialog.title or "Unknown"
                title_lower = title.lower()
                
                marketplace_keywords = ['market', 'shop', 'store', 'sell', 'buy', 'trade', 'deal', 'bazaar', 'mall', 'marketplace', 'bazar', 'selling', 'buying']
                for keyword in marketplace_keywords:
                    if keyword in title_lower:
                        is_marketplace = True
                        break
                
                access_hash = getattr(entity, 'access_hash', None)
                
                item = {
                    'id': entity.id,
                    'title': title,
                    'is_marketplace': is_marketplace,
                    'members': getattr(entity, 'participants_count', 0) or 0,
                    'access_hash': access_hash
                }
                
                if is_marketplace:
                    marketplaces.append(item)
                else:
                    groups.append(item)
        
        await client.disconnect()
        
        await database.create_or_update_stats(
            account_id,
            groups_count=len(groups),
            marketplaces_count=len(marketplaces)
        )
        
        return {
            "success": True,
            "groups": groups,
            "marketplaces": marketplaces,
            "total": len(groups) + len(marketplaces)
        }
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        return {"success": False, "error": str(e)}

async def send_message_to_chat(account_id, chat_id, message, access_hash=None, use_forward=False, source_message_id=None):
    try:
        if isinstance(account_id, str):
            account_id = ObjectId(account_id)
        account = await database.get_account(account_id)
        if not account or not account.get('is_logged_in'):
            return {"success": False, "error": "Account not logged in"}
        
        api_id = decrypt_data(account.get('api_id', ''))
        api_hash = decrypt_data(account.get('api_hash', ''))
        session_string = decrypt_data(account.get('session_string', ''))
        
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Session expired"}
        
        try:
            entity = await client.get_entity(chat_id)
        except ValueError:
            if access_hash is not None:
                entity = InputPeerChannel(channel_id=chat_id, access_hash=access_hash)
            else:
                entity = chat_id
        
        if use_forward and source_message_id:
            me = await client.get_me()
            await client.forward_messages(entity, source_message_id, me)
        else:
            await client.send_message(entity, message)
        
        await client.disconnect()
        
        await database.update_account(account_id, last_used=datetime.utcnow())
        await database.increment_stats(account_id, "messages_sent")
        
        return {"success": True}
    except Exception as e:
        await database.increment_stats(account_id, "messages_failed")
        return {"success": False, "error": str(e)}

async def save_message_to_saved(account_id, message):
    try:
        if isinstance(account_id, str):
            account_id = ObjectId(account_id)
        account = await database.get_account(account_id)
        if not account or not account.get('is_logged_in'):
            return {"success": False, "error": "Account not logged in"}
        
        api_id = decrypt_data(account.get('api_id', ''))
        api_hash = decrypt_data(account.get('api_hash', ''))
        session_string = decrypt_data(account.get('session_string', ''))
        
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Session expired"}
        
        me = await client.get_me()
        sent_msg = await client.send_message(me, message)
        
        await client.disconnect()
        
        return {"success": True, "message_id": sent_msg.id}
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return {"success": False, "error": str(e)}

async def forward_message_to_chat(account_id, chat_id, from_peer, message_id, access_hash=None):
    try:
        if isinstance(account_id, str):
            account_id = ObjectId(account_id)
        account = await database.get_account(account_id)
        if not account or not account.get('is_logged_in'):
            return {"success": False, "error": "Account not logged in"}
        
        api_id = decrypt_data(account.get('api_id', ''))
        api_hash = decrypt_data(account.get('api_hash', ''))
        session_string = decrypt_data(account.get('session_string', ''))
        
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Session expired"}
        
        try:
            entity = await client.get_entity(chat_id)
        except ValueError:
            if access_hash is not None:
                entity = InputPeerChannel(channel_id=chat_id, access_hash=access_hash)
            else:
                entity = chat_id
        
        await client.forward_messages(entity, message_id, from_peer)
        
        await client.disconnect()
        
        await database.update_account(account_id, last_used=datetime.utcnow())
        await database.increment_stats(account_id, "messages_sent")
        
        return {"success": True}
    except Exception as e:
        await database.increment_stats(account_id, "messages_failed")
        return {"success": False, "error": str(e)}

async def broadcast_message(account_id, message, delay=60, use_forward=False):
    result = await get_groups_and_marketplaces(account_id)
    if not result["success"]:
        return result
    
    all_chats = result["groups"] + result["marketplaces"]
    sent = 0
    failed = 0
    source_message_id = None
    
    if use_forward:
        save_result = await save_message_to_saved(account_id, message)
        if save_result["success"]:
            source_message_id = save_result["message_id"]
        else:
            use_forward = False
    
    for chat in all_chats:
        try:
            if use_forward and source_message_id:
                if isinstance(account_id, str):
                    acc_id = ObjectId(account_id)
                else:
                    acc_id = account_id
                account = await database.get_account(acc_id)
                api_id = decrypt_data(account.get('api_id', ''))
                api_hash = decrypt_data(account.get('api_hash', ''))
                session_string = decrypt_data(account.get('session_string', ''))
                
                client = TelegramClient(StringSession(session_string), api_id, api_hash)
                await client.connect()
                
                if await client.is_user_authorized():
                    me = await client.get_me()
                    try:
                        entity = await client.get_entity(chat["id"])
                    except ValueError:
                        if chat.get("access_hash") is not None:
                            entity = InputPeerChannel(channel_id=chat["id"], access_hash=chat.get("access_hash"))
                        else:
                            entity = chat["id"]
                    
                    await client.forward_messages(entity, source_message_id, me)
                    await database.increment_stats(account_id, "messages_sent")
                    sent += 1
                else:
                    failed += 1
                
                await client.disconnect()
            else:
                send_result = await send_message_to_chat(account_id, chat["id"], message, chat.get("access_hash"))
                if send_result["success"]:
                    sent += 1
                else:
                    failed += 1
            
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            failed += 1
    
    if isinstance(account_id, str):
        account_id = ObjectId(account_id)
    await database.create_or_update_stats(account_id, last_broadcast=datetime.utcnow())
    
    return {
        "success": True,
        "sent": sent,
        "failed": failed,
        "total": len(all_chats)
    }

async def get_account_info(api_id, api_hash, session_string):
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Not authorized"}
        
        me = await client.get_me()
        await client.disconnect()
        
        return {
            "success": True,
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "username": me.username or "",
            "phone": me.phone or ""
        }
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return {"success": False, "error": str(e)}

async def update_account_profile(api_id, api_hash, session_string, first_name=None, last_name=None, about=None):
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Not authorized"}
        
        await client(UpdateProfileRequest(
            first_name=first_name,
            last_name=last_name,
            about=about
        ))
        
        new_session = client.session.save()
        await client.disconnect()
        
        return {"success": True, "session_string": new_session}
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return {"success": False, "error": str(e)}

async def update_account_bio(api_id, api_hash, session_string, bio):
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Not authorized"}
        
        await client(UpdateProfileRequest(about=bio))
        
        new_session = client.session.save()
        await client.disconnect()
        
        return {"success": True, "session_string": new_session}
    except Exception as e:
        logger.error(f"Error updating bio: {e}")
        return {"success": False, "error": str(e)}

async def update_account_name(api_id, api_hash, session_string, first_name, last_name=None):
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Not authorized"}
        
        await client(UpdateProfileRequest(
            first_name=first_name,
            last_name=last_name if last_name else ""
        ))
        
        new_session = client.session.save()
        await client.disconnect()
        
        return {"success": True, "session_string": new_session}
    except Exception as e:
        logger.error(f"Error updating name: {e}")
        return {"success": False, "error": str(e)}

async def join_group_by_link(account_id, invite_link):
    try:
        if isinstance(account_id, str):
            account_id = ObjectId(account_id)
        account = await database.get_account(account_id)
        if not account or not account.get('is_logged_in'):
            return {"success": False, "error": "Account not logged in"}
        
        api_id = decrypt_data(account.get('api_id', ''))
        api_hash = decrypt_data(account.get('api_hash', ''))
        session_string = decrypt_data(account.get('session_string', ''))
        
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Session expired"}
        
        hash_pattern = re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/(?:joinchat/|\+)([a-zA-Z0-9_-]+)')
        username_pattern = re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z][a-zA-Z0-9_]{4,})')
        
        hash_match = hash_pattern.search(invite_link)
        username_match = username_pattern.search(invite_link)
        
        group_title = None
        group_id = None
        
        if hash_match:
            invite_hash = hash_match.group(1)
            try:
                result = await client(ImportChatInviteRequest(invite_hash))
                if hasattr(result, 'chats') and result.chats:
                    chat = result.chats[0]
                    group_title = getattr(chat, 'title', None)
                    group_id = chat.id
            except UserAlreadyParticipantError:
                await client.disconnect()
                return {"success": False, "error": "Already a member of this group"}
            except (InviteHashExpiredError, InviteHashInvalidError):
                await client.disconnect()
                return {"success": False, "error": "Invalid or expired invite link"}
        elif username_match:
            username = username_match.group(1)
            try:
                entity = await client.get_entity(username)
                await client(JoinChannelRequest(entity))
                group_title = getattr(entity, 'title', None)
                group_id = entity.id
            except UserAlreadyParticipantError:
                await client.disconnect()
                return {"success": False, "error": "Already a member of this group"}
        else:
            await client.disconnect()
            return {"success": False, "error": "Invalid invite link format"}
        
        await client.disconnect()
        
        await database.log_group_join(account_id, group_id, group_title, invite_link)
        await database.increment_stats(account_id, "groups_joined")
        
        return {"success": True, "group_title": group_title, "group_id": group_id}
    except Exception as e:
        logger.error(f"Error joining group: {e}")
        return {"success": False, "error": str(e)}

async def send_auto_reply(account_id, to_user_id, reply_text):
    try:
        if isinstance(account_id, str):
            account_id = ObjectId(account_id)
        account = await database.get_account(account_id)
        if not account or not account.get('is_logged_in'):
            return {"success": False, "error": "Account not logged in"}
        
        api_id = decrypt_data(account.get('api_id', ''))
        api_hash = decrypt_data(account.get('api_hash', ''))
        session_string = decrypt_data(account.get('session_string', ''))
        
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Session expired"}
        
        await client.send_message(to_user_id, reply_text)
        await client.disconnect()
        
        await database.increment_stats(account_id, "auto_replies_sent")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error sending auto reply: {e}")
        return {"success": False, "error": str(e)}

async def apply_profile_changes(api_id, api_hash, session_string):
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"success": False, "error": "Not authorized"}
        
        me = await client.get_me()
        current_name = me.first_name or ""
        
        new_first_name = current_name
        if config.ACCOUNT_NAME_SUFFIX and config.ACCOUNT_NAME_SUFFIX not in current_name:
            new_first_name = f"{current_name} {config.ACCOUNT_NAME_SUFFIX}"
        
        await client(UpdateProfileRequest(
            first_name=new_first_name,
            about=config.ACCOUNT_BIO_TEMPLATE
        ))
        
        new_session = client.session.save()
        await client.disconnect()
        
        return {"success": True, "session_string": new_session, "first_name": new_first_name}
    except Exception as e:
        logger.error(f"Error applying profile changes: {e}")
        return {"success": False, "error": str(e)}
