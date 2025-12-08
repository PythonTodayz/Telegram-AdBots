import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from telegram.constants import ParseMode
from PyToday import database
from PyToday.encryption import encrypt_data, decrypt_data
from PyToday.keyboards import (
    main_menu_keyboard, otp_keyboard, accounts_keyboard, 
    groups_keyboard, delete_accounts_keyboard, confirm_delete_keyboard,
    time_keyboard, back_to_menu_keyboard, account_selection_keyboard,
    ad_text_menu_keyboard, ad_text_back_keyboard, settings_keyboard,
    twofa_keyboard, back_to_settings_keyboard, advertising_menu_keyboard,
    accounts_menu_keyboard, support_keyboard, target_adv_keyboard,
    selected_groups_keyboard, target_groups_list_keyboard, remove_groups_keyboard,
    single_account_selection_keyboard
)
from PyToday import telethon_handler
from PyToday import config

logger = logging.getLogger(__name__)
user_states = {}

async def safe_edit_message(query, text, parse_mode="Markdown", reply_markup=None):
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Failed to edit message: {e}")

async def safe_edit_caption(query, text, parse_mode="Markdown", reply_markup=None):
    try:
        await query.edit_message_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Failed to edit caption: {e}")

async def send_notification(query, text, reply_markup=None):
    try:
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def is_admin(user_id):
    return user_id in config.ADMIN_USER_IDS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    await database.save_bot_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    db_user = await database.get_user(user.id)
    if not db_user:
        await database.create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
    
    if config.ADMIN_ONLY_MODE and not is_admin(user.id):
        private_text = """
⚠️ *ᴘʀɪᴠᴀᴛᴇ ʙᴏᴛ*

> _This bot is for personal use only._
> _Contact the admin for access._

👨‍💻 [Contact Admin](tg://user?id=7756391784)
"""
        try:
            await update.message.reply_photo(
                photo=config.START_IMAGE_URL,
                caption=private_text,
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text(private_text, parse_mode="Markdown")
        return
    
    total_users = await database.get_bot_users_count()
    
    welcome_text = f"""
🤖 *ᴛᴇʟᴇɢʀᴀᴍ ᴀᴅ ʙᴏᴛ*

> 👋 *Welcome,* `{user.first_name}`!
> 👥 *Total Users:* `{total_users}`
"""
    
    try:
        await update.message.reply_photo(
            photo=config.START_IMAGE_URL,
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to send photo: {e}")
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⚠️ *This command is only for admins.*", parse_mode="Markdown")
        return
    
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            "📢 *ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴍᴀɴᴅ*\n\n"
            "> Reply to a message or send:\n"
            "> `/broadcast Your message here`\n\n"
            "_Supports: Text, Photo, Video, Document, Audio_",
            parse_mode="Markdown"
        )
        return
    
    user_states[user.id] = {"state": "broadcasting", "data": {}}
    
    all_users = await database.get_all_bot_users()
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text(
        f"📤 *Broadcasting...*\n\n"
        f"👥 Total: `{len(all_users)}`\n"
        f"✅ Sent: `0`\n"
        f"❌ Failed: `0`",
        parse_mode="Markdown"
    )
    
    for bot_user in all_users:
        try:
            if update.message.reply_to_message:
                reply_msg = update.message.reply_to_message
                if reply_msg.photo:
                    await context.bot.send_photo(
                        bot_user["_id"],
                        reply_msg.photo[-1].file_id,
                        caption=reply_msg.caption,
                        parse_mode="Markdown"
                    )
                elif reply_msg.video:
                    await context.bot.send_video(
                        bot_user["_id"],
                        reply_msg.video.file_id,
                        caption=reply_msg.caption,
                        parse_mode="Markdown"
                    )
                elif reply_msg.document:
                    await context.bot.send_document(
                        bot_user["_id"],
                        reply_msg.document.file_id,
                        caption=reply_msg.caption,
                        parse_mode="Markdown"
                    )
                elif reply_msg.audio:
                    await context.bot.send_audio(
                        bot_user["_id"],
                        reply_msg.audio.file_id,
                        caption=reply_msg.caption,
                        parse_mode="Markdown"
                    )
                elif reply_msg.voice:
                    await context.bot.send_voice(
                        bot_user["_id"],
                        reply_msg.voice.file_id,
                        caption=reply_msg.caption
                    )
                elif reply_msg.sticker:
                    await context.bot.send_sticker(
                        bot_user["_id"],
                        reply_msg.sticker.file_id
                    )
                else:
                    await context.bot.send_message(
                        bot_user["_id"],
                        reply_msg.text or reply_msg.caption,
                        parse_mode="Markdown"
                    )
            else:
                text = " ".join(context.args)
                await context.bot.send_message(
                    bot_user["_id"],
                    text,
                    parse_mode="Markdown"
                )
            sent += 1
        except Exception as e:
            logger.error(f"Broadcast failed for {bot_user['_id']}: {e}")
            failed += 1
        
        if (sent + failed) % 10 == 0:
            try:
                await status_msg.edit_text(
                    f"📤 *Broadcasting...*\n\n"
                    f"👥 Total: `{len(all_users)}`\n"
                    f"✅ Sent: `{sent}`\n"
                    f"❌ Failed: `{failed}`",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        await asyncio.sleep(0.05)
    
    if user.id in user_states:
        del user_states[user.id]
    
    await status_msg.edit_text(
        f"✅ *ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ*\n\n"
        f"👥 Total: `{len(all_users)}`\n"
        f"✅ Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`",
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    await query.answer()
    
    if config.ADMIN_ONLY_MODE and not is_admin(user_id):
        await query.answer("⚠️ This bot is for personal use only.", show_alert=True)
        return
    
    if data.startswith("otp_"):
        await handle_otp_input(query, user_id, data, context)
        return
    
    if data == "twofa_cancel":
        if user_id in user_states:
            del user_states[user_id]
        await send_new_message(query, "❌ *2FA verification cancelled.*\n\n> _Returning to main menu..._", main_menu_keyboard())
        return
    
    if data == "main_menu":
        await show_main_menu(query)
    
    elif data == "advertising_menu":
        await show_advertising_menu(query)
    
    elif data == "accounts_menu":
        await show_accounts_menu(query)
    
    elif data == "support":
        await show_support(query)
    
    elif data == "settings":
        await show_settings(query, user_id)
    
    elif data == "toggle_forward_mode":
        await toggle_forward_mode(query, user_id)
    
    elif data == "toggle_auto_reply":
        await toggle_auto_reply(query, user_id)
    
    elif data == "toggle_auto_group_join":
        await toggle_auto_group_join(query, user_id)
    
    elif data == "target_adv":
        await show_target_adv(query, user_id)
    
    elif data == "target_all_groups":
        await set_target_all_groups(query, user_id)
    
    elif data == "target_selected_groups":
        await show_selected_groups_menu(query, user_id)
    
    elif data == "add_target_group":
        await prompt_add_target_group(query, user_id)
    
    elif data == "remove_target_group":
        await show_remove_target_groups(query, user_id)
    
    elif data.startswith("rm_tg_"):
        group_id = int(data.split("_")[2])
        await remove_target_group(query, user_id, group_id)
    
    elif data == "clear_target_groups":
        await clear_all_target_groups(query, user_id)
    
    elif data == "view_target_groups":
        await view_target_groups(query, user_id)
    
    elif data == "add_account":
        await start_add_account(query, user_id)
    
    elif data == "delete_account":
        await show_delete_accounts(query, user_id)
    
    elif data.startswith("del_acc_"):
        account_id = data.split("_")[2]
        await confirm_delete_account(query, account_id)
    
    elif data.startswith("confirm_del_"):
        account_id = data.split("_")[2]
        await delete_account(query, user_id, account_id)
    
    elif data.startswith("del_page_"):
        page = int(data.split("_")[2])
        await show_delete_accounts(query, user_id, page)
    
    elif data == "load_groups":
        await load_groups(query, user_id)
    
    elif data.startswith("grp_page_"):
        parts = data.split("_")
        account_id = parts[2]
        page = int(parts[3])
        await load_account_groups_page(query, user_id, account_id, page, context)
    
    elif data.startswith("load_grp_"):
        account_id = data.split("_")[2]
        await load_account_groups(query, user_id, account_id, context)
    
    elif data == "statistics":
        await show_statistics(query, user_id)
    
    elif data == "set_ad_text":
        await show_ad_text_menu(query, user_id)
    
    elif data == "ad_saved_text":
        await show_saved_ad_text(query, user_id)
    
    elif data == "ad_add_text":
        await prompt_ad_text(query, user_id)
    
    elif data == "ad_delete_text":
        await delete_ad_text(query, user_id)
    
    elif data == "set_time":
        await show_time_options(query)
    
    elif data.startswith("time_"):
        time_val = data.split("_")[1]
        await set_time_interval(query, user_id, time_val)
    
    elif data == "single_mode":
        await set_single_mode(query, user_id)
    
    elif data == "multiple_mode":
        await set_multiple_mode(query, user_id, context)
    
    elif data.startswith("toggle_acc_"):
        account_id = data.split("_")[2]
        await toggle_account_selection(query, user_id, account_id, context)
    
    elif data.startswith("sel_page_"):
        page = int(data.split("_")[2])
        await show_account_selection(query, user_id, page, context)
    
    elif data == "confirm_selection":
        await confirm_account_selection(query, user_id, context)
    
    elif data == "my_accounts":
        await show_my_accounts(query, user_id)
    
    elif data.startswith("acc_page_"):
        page = int(data.split("_")[2])
        await show_my_accounts(query, user_id, page)
    
    elif data == "start_advertising":
        await start_advertising(query, user_id, context)
    
    elif data == "stop_advertising":
        context.user_data["advertising_active"] = False
        await send_new_message(
            query,
            "🛑 *ᴀᴅᴠᴇʀᴛɪsɪɴɢ sᴛᴏᴘᴘᴇᴅ*\n\n> ✅ _Your campaign has been stopped successfully._",
            advertising_menu_keyboard()
        )
    
    elif data.startswith("select_single_"):
        account_id = data.split("_")[2]
        await select_single_account(query, user_id, account_id)
    
    elif data.startswith("single_page_"):
        page = int(data.split("_")[2])
        await show_single_account_page(query, user_id, page)

async def send_new_message(query, text, reply_markup=None):
    try:
        try:
            await query.edit_message_caption(caption=text, parse_mode="Markdown", reply_markup=reply_markup)
        except:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            try:
                await query.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
            except Exception as ex:
                logger.error(f"Failed to send message: {ex}")

async def show_main_menu(query):
    if user_states.get(query.from_user.id):
        del user_states[query.from_user.id]
    
    total_users = await database.get_bot_users_count()
    
    menu_text = f"""
🤖 *ᴛᴇʟᴇɢʀᴀᴍ ᴀᴅ ʙᴏᴛ*

━━━━━━━━━━━━━━━━━━
👥 *Total Users:* `{total_users}`
━━━━━━━━━━━━━━━━━━

> _Select an option below:_
"""
    
    await send_new_message(query, menu_text, main_menu_keyboard())

async def show_advertising_menu(query):
    adv_text = """
📢 *ᴀᴅᴠᴇʀᴛɪsɪɴɢ ᴍᴇɴᴜ*

━━━━━━━━━━━━━━━━━━
🚀 *Start* - Begin advertising
🛑 *Stop* - Stop advertising
⏱️ *Set Time* - Change interval
━━━━━━━━━━━━━━━━━━

> _Select an option:_
"""
    await send_new_message(query, adv_text, advertising_menu_keyboard())

async def show_accounts_menu(query):
    acc_text = """
👤 *ᴀᴄᴄᴏᴜɴᴛs ᴍᴇɴᴜ*

━━━━━━━━━━━━━━━━━━
➕ *Add* - Add new account
🗑️ *Delete* - Remove account
📋 *My Accounts* - View all
━━━━━━━━━━━━━━━━━━

> _Select an option:_
"""
    await send_new_message(query, acc_text, accounts_menu_keyboard())

async def show_support(query):
    support_text = """
💬 *sᴜᴘᴘᴏʀᴛ*

> *Need help? Contact us!*
> *Check the tutorial to get started.*
"""
    await send_new_message(query, support_text, support_keyboard())

async def show_settings(query, user_id):
    user = await database.get_user(user_id)
    use_multiple = user.get('use_multiple_accounts', False) if user else False
    use_forward = user.get('use_forward_mode', False) if user else False
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    auto_group_join = user.get('auto_group_join_enabled', False) if user else False
    
    mode_text = "📱📱 Multiple" if use_multiple else "📱 Single"
    forward_text = "✉️ Forward" if use_forward else "📤 Send"
    auto_reply_text = "🟢 ON" if auto_reply else "🔴 OFF"
    auto_join_text = "🟢 ON" if auto_group_join else "🔴 OFF"
    
    settings_text = f"""
⚙️ *sᴇᴛᴛɪɴɢs*

━━━━━━━━━━━━━━━━━━
📊 *Current Configuration:*

> 🔹 *Account Mode:* {mode_text}
> 🔹 *Message Mode:* {forward_text}
> 🔹 *Auto Reply:* {auto_reply_text}
> 🔹 *Auto Join:* {auto_join_text}
━━━━━━━━━━━━━━━━━━

> _Tap to change settings:_
"""
    
    await send_new_message(query, settings_text, settings_keyboard(use_multiple, use_forward, auto_reply, auto_group_join))

async def toggle_forward_mode(query, user_id):
    user = await database.get_user(user_id)
    current_mode = user.get('use_forward_mode', False) if user else False
    new_mode = not current_mode
    
    await database.update_user(user_id, use_forward_mode=new_mode)
    
    user = await database.get_user(user_id)
    use_multiple = user.get('use_multiple_accounts', False) if user else False
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    auto_group_join = user.get('auto_group_join_enabled', False) if user else False
    
    if new_mode:
        mode_text = "✉️ *ғᴏʀᴡᴀʀᴅ ᴍᴏᴅᴇ*"
        description = "> _Messages will be forwarded with premium emojis preserved_"
        icon = "🟢"
    else:
        mode_text = "📤 *sᴇɴᴅ ᴍᴏᴅᴇ*"
        description = "> _Messages will be sent directly_"
        icon = "🔴"
    
    result_text = f"""
{icon} *ᴍᴏᴅᴇ ᴄʜᴀɴɢᴇᴅ*

━━━━━━━━━━━━━━━━━━
✅ Changed to: {mode_text}

{description}
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, settings_keyboard(use_multiple, new_mode, auto_reply, auto_group_join))

async def toggle_auto_reply(query, user_id):
    user = await database.get_user(user_id)
    current_mode = user.get('auto_reply_enabled', False) if user else False
    new_mode = not current_mode
    
    await database.update_user(user_id, auto_reply_enabled=new_mode)
    
    user = await database.get_user(user_id)
    use_multiple = user.get('use_multiple_accounts', False) if user else False
    use_forward = user.get('use_forward_mode', False) if user else False
    auto_group_join = user.get('auto_group_join_enabled', False) if user else False
    
    status = "🟢 ON" if new_mode else "🔴 OFF"
    
    result_text = f"""
💬 *ᴀᴜᴛᴏ ʀᴇᴘʟʏ*

━━━━━━━━━━━━━━━━━━
✅ Auto Reply is now: *{status}*

> _When enabled, accounts will auto-reply to DMs_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, settings_keyboard(use_multiple, use_forward, new_mode, auto_group_join))

async def toggle_auto_group_join(query, user_id):
    user = await database.get_user(user_id)
    current_mode = user.get('auto_group_join_enabled', False) if user else False
    new_mode = not current_mode
    
    await database.update_user(user_id, auto_group_join_enabled=new_mode)
    
    user = await database.get_user(user_id)
    use_multiple = user.get('use_multiple_accounts', False) if user else False
    use_forward = user.get('use_forward_mode', False) if user else False
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    
    status = "🟢 ON" if new_mode else "🔴 OFF"
    
    result_text = f"""
🔗 *ᴀᴜᴛᴏ ɢʀᴏᴜᴘ ᴊᴏɪɴ*

━━━━━━━━━━━━━━━━━━
✅ Auto Join is now: *{status}*

> _When enabled, accounts will auto-join groups from links_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, settings_keyboard(use_multiple, use_forward, auto_reply, new_mode))

async def show_target_adv(query, user_id):
    user = await database.get_user(user_id)
    target_mode = user.get('target_mode', 'all') if user else 'all'
    
    target_text = f"""
🎯 *ᴛᴀʀɢᴇᴛ ᴀᴅᴠᴇʀᴛɪsɪɴɢ*

━━━━━━━━━━━━━━━━━━
📊 *Current Mode:* `{target_mode.upper()}`

> 📢 *All Groups* - Send to all groups
> 🎯 *Selected* - Send to specific groups
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, target_text, target_adv_keyboard(target_mode))

async def set_target_all_groups(query, user_id):
    await database.update_user(user_id, target_mode="all")
    
    result_text = """
✅ *ᴛᴀʀɢᴇᴛ sᴇᴛ*

━━━━━━━━━━━━━━━━━━
📢 Target Mode: *ALL GROUPS*

> _Messages will be sent to all groups_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, target_adv_keyboard("all"))

async def show_selected_groups_menu(query, user_id):
    await database.update_user(user_id, target_mode="selected")
    
    target_groups = await database.get_target_groups(user_id)
    
    menu_text = f"""
🎯 *sᴇʟᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘs*

━━━━━━━━━━━━━━━━━━
📊 *Selected Groups:* `{len(target_groups)}`

> ➕ Add groups by ID
> ➖ Remove groups
> 📋 View all selected
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, menu_text, selected_groups_keyboard())

async def prompt_add_target_group(query, user_id):
    user_states[user_id] = {"state": "awaiting_target_group_id", "data": {}}
    
    prompt_text = """
➕ *ᴀᴅᴅ ɢʀᴏᴜᴘ*

━━━━━━━━━━━━━━━━━━
> _Send the Group ID to add:_

💡 *How to get Group ID:*
Forward a message from the group to @userinfobot
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, prompt_text, back_to_menu_keyboard())

async def remove_target_group(query, user_id, group_id):
    removed = await database.remove_target_group(user_id, group_id)
    
    if removed:
        result_text = f"""
✅ *ɢʀᴏᴜᴘ ʀᴇᴍᴏᴠᴇᴅ*

━━━━━━━━━━━━━━━━━━
🗑️ Group `{group_id}` removed successfully.
━━━━━━━━━━━━━━━━━━
"""
    else:
        result_text = """
❌ *ғᴀɪʟᴇᴅ*

━━━━━━━━━━━━━━━━━━
⚠️ Group not found in your list.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, selected_groups_keyboard())

async def show_remove_target_groups(query, user_id, page=0):
    target_groups = await database.get_target_groups(user_id)
    
    if not target_groups:
        no_groups_text = """
❌ *ɴᴏ ɢʀᴏᴜᴘs*

━━━━━━━━━━━━━━━━━━
⚠️ No groups in your target list.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_groups_text, selected_groups_keyboard())
        return
    
    remove_text = f"""
➖ *ʀᴇᴍᴏᴠᴇ ɢʀᴏᴜᴘs*

━━━━━━━━━━━━━━━━━━
📊 Total Groups: `{len(target_groups)}`

> _Tap a group to remove:_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, remove_text, remove_groups_keyboard(target_groups, page))

async def clear_all_target_groups(query, user_id):
    count = await database.clear_target_groups(user_id)
    
    result_text = f"""
✅ *ᴄʟᴇᴀʀᴇᴅ*

━━━━━━━━━━━━━━━━━━
🗑️ Removed `{count}` groups from target list.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, selected_groups_keyboard())

async def view_target_groups(query, user_id, page=0):
    target_groups = await database.get_target_groups(user_id)
    
    if not target_groups:
        no_groups_text = """
❌ *ɴᴏ ɢʀᴏᴜᴘs*

━━━━━━━━━━━━━━━━━━
⚠️ No groups in your target list.

💡 Use *Add Group* to add groups.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_groups_text, selected_groups_keyboard())
        return
    
    view_text = f"""
📋 *ᴛᴀʀɢᴇᴛ ɢʀᴏᴜᴘs*

━━━━━━━━━━━━━━━━━━
📊 Total: `{len(target_groups)}`
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, view_text, target_groups_list_keyboard(target_groups, page))

async def start_add_account(query, user_id):
    user_states[user_id] = {
        "state": "awaiting_api_id",
        "data": {}
    }
    
    add_text = """
📱 *ᴀᴅᴅ ɴᴇᴡ ᴀᴄᴄᴏᴜɴᴛ*

━━━━━━━━━━━━━━━━━━
📍 *Step 1/4:* Enter your `API ID`

> 🔗 Get it from: my.telegram.org
> 💡 Go to *API Development Tools*
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, add_text, back_to_menu_keyboard())

async def show_delete_accounts(query, user_id, page=0):
    accounts = await database.get_accounts(user_id)
    
    if not accounts:
        no_acc_text = """
❌ *ɴᴏ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
⚠️ You haven't added any accounts.

💡 Use *Add Account* to add one.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_acc_text, accounts_menu_keyboard())
        return
    
    del_text = f"""
🗑️ *ᴅᴇʟᴇᴛᴇ ᴀᴄᴄᴏᴜɴᴛ*

━━━━━━━━━━━━━━━━━━
📊 Total Accounts: `{len(accounts)}`

> ⚠️ _Select an account to delete:_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, del_text, delete_accounts_keyboard(accounts, page))

async def confirm_delete_account(query, account_id):
    account = await database.get_account(account_id)
    if account:
        confirm_text = f"""
⚠️ *ᴄᴏɴғɪʀᴍ ᴅᴇʟᴇᴛᴇ*

━━━━━━━━━━━━━━━━━━
🔴 *Are you sure?*

📱 Phone: `{account.get('phone', 'Unknown')}`

> ⚠️ _This cannot be undone!_
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, confirm_text, confirm_delete_keyboard(account_id))

async def delete_account(query, user_id, account_id):
    account = await database.get_account(account_id)
    phone = account.get('phone', 'Unknown') if account else 'Unknown'
    
    deleted = await database.delete_account(account_id, user_id)
    
    if deleted:
        success_text = f"""
✅ *ᴀᴄᴄᴏᴜɴᴛ ᴅᴇʟᴇᴛᴇᴅ*

━━━━━━━━━━━━━━━━━━
📱 Phone: `{phone}`

🗑️ _Removed successfully._
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, success_text, accounts_menu_keyboard())
    else:
        fail_text = """
❌ *ᴅᴇʟᴇᴛᴇ ғᴀɪʟᴇᴅ*

━━━━━━━━━━━━━━━━━━
⚠️ Account not found.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, fail_text, accounts_menu_keyboard())

async def load_groups(query, user_id, page=0):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if not accounts:
        no_acc_text = """
❌ *ɴᴏ ʟᴏɢɢᴇᴅ-ɪɴ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
⚠️ You don't have any logged-in accounts.

💡 Please add and login to an account first.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_acc_text, main_menu_keyboard())
        return
    
    keyboard = []
    
    for acc in accounts:
        stats = await database.get_account_stats(acc.get('_id'))
        groups_count = stats.get('groups_count', 0) if stats else 0
        mps_count = stats.get('marketplaces_count', 0) if stats else 0
        keyboard.append([InlineKeyboardButton(
            f"📱 {acc.get('phone', 'Unknown')} (👥 {groups_count} | 🏪 {mps_count})",
            callback_data=f"load_grp_{acc.get('_id')}"
        )])
    
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    load_text = f"""
📂 *ʟᴏᴀᴅ ɢʀᴏᴜᴘs & ᴍᴀʀᴋᴇᴛᴘʟᴀᴄᴇs*

━━━━━━━━━━━━━━━━━━
📊 Logged-in Accounts: `{len(accounts)}`

> _Select an account to load groups:_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, load_text, InlineKeyboardMarkup(keyboard))

async def load_account_groups(query, user_id, account_id, context):
    loading_text = """
⏳ *ʟᴏᴀᴅɪɴɢ...*

━━━━━━━━━━━━━━━━━━
🔄 _Fetching groups and marketplaces..._
━━━━━━━━━━━━━━━━━━
"""
    await send_new_message(query, loading_text, None)
    
    result = await telethon_handler.get_groups_and_marketplaces(account_id)
    
    if not result["success"]:
        error_text = f"""
❌ *ᴇʀʀᴏʀ*

━━━━━━━━━━━━━━━━━━
⚠️ `{result['error']}`
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, error_text, main_menu_keyboard())
        return
    
    groups = result["groups"]
    marketplaces = result["marketplaces"]
    all_items = groups + marketplaces
    
    context.user_data[f"groups_{account_id}"] = all_items
    
    if not all_items:
        no_groups_text = """
📂 *ɴᴏ ɢʀᴏᴜᴘs ғᴏᴜɴᴅ*

━━━━━━━━━━━━━━━━━━
⚠️ No groups or marketplaces found.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_groups_text, main_menu_keyboard())
        return
    
    success_text = f"""
📂 *ɢʀᴏᴜᴘs & ᴍᴀʀᴋᴇᴛᴘʟᴀᴄᴇs*

━━━━━━━━━━━━━━━━━━
📊 *Statistics:*
> 👥 Groups: `{len(groups)}`
> 🏪 Marketplaces: `{len(marketplaces)}`
> 📊 Total: `{len(all_items)}`
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, success_text, groups_keyboard(all_items, account_id, 0))

async def load_account_groups_page(query, user_id, account_id, page, context):
    all_items = context.user_data.get(f"groups_{account_id}", [])
    
    if not all_items:
        result = await telethon_handler.get_groups_and_marketplaces(account_id)
        if result["success"]:
            all_items = result["groups"] + result["marketplaces"]
            context.user_data[f"groups_{account_id}"] = all_items
    
    if not all_items:
        no_groups_text = """
📂 *ɴᴏ ɢʀᴏᴜᴘs*

━━━━━━━━━━━━━━━━━━
⚠️ Please reload groups.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_groups_text, main_menu_keyboard())
        return
    
    groups_count = sum(1 for g in all_items if not g.get('is_marketplace'))
    marketplaces_count = len(all_items) - groups_count
    
    page_text = f"""
📂 *ɢʀᴏᴜᴘs* _(Page {page + 1})_

━━━━━━━━━━━━━━━━━━
> 👥 Groups: `{groups_count}`
> 🏪 Marketplaces: `{marketplaces_count}`
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, page_text, groups_keyboard(all_items, account_id, page))

async def show_statistics(query, user_id):
    accounts = await database.get_accounts(user_id)
    
    total_accounts = len(accounts)
    logged_in = sum(1 for a in accounts if a.get('is_logged_in'))
    total_sent = 0
    total_failed = 0
    total_groups = 0
    total_mps = 0
    total_joined = 0
    total_auto_replies = 0
    
    for acc in accounts:
        stats = await database.get_account_stats(acc.get('_id'))
        if stats:
            total_sent += stats.get('messages_sent', 0)
            total_failed += stats.get('messages_failed', 0)
            total_groups += stats.get('groups_count', 0)
            total_mps += stats.get('marketplaces_count', 0)
            total_joined += stats.get('groups_joined', 0)
            total_auto_replies += stats.get('auto_replies_sent', 0)
    
    user = await database.get_user(user_id)
    time_interval = user.get('time_interval', 60) if user else 60
    ad_text = user.get('ad_text') if user else None
    mode = "📱📱 Multiple" if user and user.get('use_multiple_accounts') else "📱 Single"
    forward_mode = "✉️ Forward" if user and user.get('use_forward_mode') else "📤 Send"
    ad_status = "✅ Set" if ad_text else "❌ Not Set"
    
    stats_text = f"""
📊 *ʏᴏᴜʀ sᴛᴀᴛɪsᴛɪᴄs*

━━━━━━━━━━━━━━━━━━
👤 *ACCOUNTS:*
> 📊 Total: `{total_accounts}`
> 🟢 Logged In: `{logged_in}`
> 🔴 Logged Out: `{total_accounts - logged_in}`

📨 *MESSAGES:*
> ✅ Sent: `{total_sent}`
> ❌ Failed: `{total_failed}`

📂 *CHATS:*
> 👥 Groups: `{total_groups}`
> 🏪 Marketplaces: `{total_mps}`
> 🔗 Joined: `{total_joined}`

💬 *AUTO REPLIES:*
> 📤 Sent: `{total_auto_replies}`

⚙️ *SETTINGS:*
> ⏱️ Interval: `{time_interval}s`
> 📱 Mode: {mode}
> ✉️ Send Mode: {forward_mode}
> 📝 Ad Text: {ad_status}
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, stats_text, back_to_settings_keyboard())

async def show_ad_text_menu(query, user_id):
    if user_states.get(user_id):
        del user_states[user_id]
    
    user = await database.get_user(user_id)
    has_text = user and user.get('ad_text')
    status = "✅ Configured" if has_text else "❌ Not configured"
    
    ad_menu_text = f"""
📝 *ᴀᴅᴠᴇʀᴛɪsᴇᴍᴇɴᴛ ᴛᴇxᴛ*

━━━━━━━━━━━━━━━━━━
📊 Status: {status}

> _Select an option:_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, ad_menu_text, ad_text_menu_keyboard())

async def show_saved_ad_text(query, user_id):
    user = await database.get_user(user_id)
    if user and user.get('ad_text'):
        saved_text = f"""
📄 *sᴀᴠᴇᴅ ᴀᴅ ᴛᴇxᴛ*

━━━━━━━━━━━━━━━━━━
{user.get('ad_text')}
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, saved_text, ad_text_back_keyboard())
    else:
        no_text = """
❌ *ɴᴏ ᴀᴅ ᴛᴇxᴛ*

━━━━━━━━━━━━━━━━━━
⚠️ No ad text saved.

💡 Use *Add Text* to create one.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_text, ad_text_menu_keyboard())

async def prompt_ad_text(query, user_id):
    user_states[user_id] = {"state": "awaiting_ad_text", "data": {}}
    
    prompt_text = """
📝 *ᴀᴅᴅ ᴀᴅ ᴛᴇxᴛ*

━━━━━━━━━━━━━━━━━━
💬 _Send your advertisement text:_

💡 *Tips:*
> 🎨 Use emojis for attraction
> 📝 Keep it short and clear
> 📞 Include contact info
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, prompt_text, ad_text_back_keyboard())

async def delete_ad_text(query, user_id):
    user = await database.get_user(user_id)
    if user and user.get('ad_text'):
        await database.update_user(user_id, ad_text=None)
        deleted_text = """
✅ *ᴀᴅ ᴛᴇxᴛ ᴅᴇʟᴇᴛᴇᴅ*

━━━━━━━━━━━━━━━━━━
🗑️ _Removed successfully._
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, deleted_text, ad_text_menu_keyboard())
    else:
        no_text = """
❌ *ɴᴏ ᴀᴅ ᴛᴇxᴛ*

━━━━━━━━━━━━━━━━━━
⚠️ Nothing to delete.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_text, ad_text_menu_keyboard())

async def show_time_options(query):
    time_text = """
⏱️ *sᴇᴛ ᴛɪᴍᴇ ɪɴᴛᴇʀᴠᴀʟ*

━━━━━━━━━━━━━━━━━━
> _Select interval between messages:_

💡 *Recommended:* 5-15 minutes
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, time_text, time_keyboard())

async def set_time_interval(query, user_id, time_val):
    if time_val == "custom":
        user_states[user_id] = {"state": "awaiting_custom_time", "data": {}}
        custom_text = """
⏱️ *ᴄᴜsᴛᴏᴍ ᴛɪᴍᴇ*

━━━━━━━━━━━━━━━━━━
> _Enter time in seconds:_

💡 Minimum: `10` seconds
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, custom_text, back_to_menu_keyboard())
        return
    
    seconds = int(time_val)
    await database.update_user(user_id, time_interval=seconds)
    
    if seconds >= 3600:
        time_display = f"{seconds // 3600} hour(s)"
    elif seconds >= 60:
        time_display = f"{seconds // 60} minute(s)"
    else:
        time_display = f"{seconds} seconds"
    
    success_text = f"""
✅ *ᴛɪᴍᴇ sᴇᴛ*

━━━━━━━━━━━━━━━━━━
⏱️ Interval: `{time_display}`

> _Messages every `{seconds}` seconds._
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, success_text, advertising_menu_keyboard())

async def set_single_mode(query, user_id):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if not accounts:
        no_acc_text = """
❌ *ɴᴏ ᴀᴄᴄᴏᴜɴᴛs*

> *No logged in accounts found.*
> *Add an account first.*
"""
        await send_new_message(query, no_acc_text, accounts_menu_keyboard())
        return
    
    await database.update_user(user_id, use_multiple_accounts=False)
    
    select_text = """
📱 *sɪɴɢʟᴇ ᴀᴄᴄᴏᴜɴᴛ ᴍᴏᴅᴇ*

> *Select an account for advertising:*
"""
    
    await send_new_message(query, select_text, single_account_selection_keyboard(accounts))

async def select_single_account(query, user_id, account_id):
    await database.update_user(user_id, selected_single_account=account_id)
    
    account = await database.get_account(account_id)
    display_name = account.get('account_first_name', 'Unknown') if account else 'Unknown'
    
    user = await database.get_user(user_id)
    use_forward = user.get('use_forward_mode', False) if user else False
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    auto_group_join = user.get('auto_group_join_enabled', False) if user else False
    
    result_text = f"""
✅ *ᴀᴄᴄᴏᴜɴᴛ sᴇʟᴇᴄᴛᴇᴅ*

> *Account:* `{display_name}`
> *Mode:* Single Account
"""
    
    await send_new_message(query, result_text, settings_keyboard(False, use_forward, auto_reply, auto_group_join))

async def show_single_account_page(query, user_id, page):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    select_text = """
📱 *sɪɴɢʟᴇ ᴀᴄᴄᴏᴜɴᴛ ᴍᴏᴅᴇ*

> *Select an account for advertising:*
"""
    
    await send_new_message(query, select_text, single_account_selection_keyboard(accounts, page))

async def set_multiple_mode(query, user_id, context=None):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if len(accounts) < 2:
        user = await database.get_user(user_id)
        use_forward = user.get('use_forward_mode', False) if user else False
        auto_reply = user.get('auto_reply_enabled', False) if user else False
        auto_group_join = user.get('auto_group_join_enabled', False) if user else False
        
        not_enough_text = f"""
❌ *ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
⚠️ Need at least 2 logged-in accounts.

📊 Current: `{len(accounts)}` account(s)
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, not_enough_text, settings_keyboard(False, use_forward, auto_reply, auto_group_join))
        return
    
    await database.update_user(user_id, use_multiple_accounts=True)
    
    if context:
        context.user_data["selection_page"] = 0
        context.user_data["selected_accounts"] = []
    
    multiple_text = f"""
✅ *ᴍᴜʟᴛɪᴘʟᴇ ᴀᴄᴄᴏᴜɴᴛs ᴍᴏᴅᴇ*

━━━━━━━━━━━━━━━━━━
📊 Found `{len(accounts)}` accounts.

> _Select accounts to use:_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, multiple_text, account_selection_keyboard(accounts, [], 0))

async def toggle_account_selection(query, user_id, account_id, context):
    selected = context.user_data.get("selected_accounts", [])
    current_page = context.user_data.get("selection_page", 0)
    
    if account_id in selected:
        selected.remove(account_id)
    else:
        selected.append(account_id)
    
    context.user_data["selected_accounts"] = selected
    context.user_data["selection_page"] = current_page
    
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    select_text = f"""
👥 *sᴇʟᴇᴄᴛ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
✅ Selected: `{len(selected)}` account(s)

> _Tap to select/deselect:_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, select_text, account_selection_keyboard(accounts, selected, current_page))

async def show_account_selection(query, user_id, page, context):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    selected = context.user_data.get("selected_accounts", [])
    context.user_data["selection_page"] = page
    
    select_text = f"""
👥 *sᴇʟᴇᴄᴛ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
✅ Selected: `{len(selected)}` account(s)
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, select_text, account_selection_keyboard(accounts, selected, page))

async def confirm_account_selection(query, user_id, context):
    selected = context.user_data.get("selected_accounts", [])
    
    if not selected:
        accounts = await database.get_accounts(user_id, logged_in_only=True)
        no_sel_text = """
❌ *ɴᴏ sᴇʟᴇᴄᴛɪᴏɴ*

━━━━━━━━━━━━━━━━━━
⚠️ Please select at least one account.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_sel_text, account_selection_keyboard(accounts, [], 0))
        return
    
    await database.update_user(user_id, selected_accounts=selected)
    
    user = await database.get_user(user_id)
    use_forward = user.get('use_forward_mode', False) if user else False
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    auto_group_join = user.get('auto_group_join_enabled', False) if user else False
    
    confirm_text = f"""
✅ *sᴇʟᴇᴄᴛɪᴏɴ sᴀᴠᴇᴅ*

━━━━━━━━━━━━━━━━━━
📊 `{len(selected)}` accounts selected.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, confirm_text, settings_keyboard(True, use_forward, auto_reply, auto_group_join))

async def show_my_accounts(query, user_id, page=0):
    accounts = await database.get_accounts(user_id)
    
    if not accounts:
        no_acc_text = """
❌ *ɴᴏ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
⚠️ No accounts added yet.

💡 Use *Add Account* to add one.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_acc_text, accounts_menu_keyboard())
        return
    
    logged_in = sum(1 for a in accounts if a.get('is_logged_in'))
    
    my_acc_text = f"""
📋 *ᴍʏ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
📊 Total: `{len(accounts)}`
🟢 Logged In: `{logged_in}`
🔴 Logged Out: `{len(accounts) - logged_in}`

> _Select to view details:_
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, my_acc_text, accounts_keyboard(accounts, page))

async def start_advertising(query, user_id, context):
    user = await database.get_user(user_id)
    
    if not user or not user.get('ad_text'):
        no_text = """
❌ *ɴᴏ ᴀᴅ ᴛᴇxᴛ*

━━━━━━━━━━━━━━━━━━
⚠️ Please set ad text first.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_text, advertising_menu_keyboard())
        return
    
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if not accounts:
        no_acc = """
❌ *ɴᴏ ᴀᴄᴄᴏᴜɴᴛs*

━━━━━━━━━━━━━━━━━━
⚠️ No logged-in accounts found.
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, no_acc, advertising_menu_keyboard())
        return
    
    context.user_data["advertising_active"] = True
    
    use_forward = user.get('use_forward_mode', False)
    time_interval = user.get('time_interval', 60)
    ad_text = user.get('ad_text')
    
    starting_text = f"""
🚀 *ᴀᴅᴠᴇʀᴛɪsɪɴɢ sᴛᴀʀᴛᴇᴅ*

━━━━━━━━━━━━━━━━━━
📊 Accounts: `{len(accounts)}`
⏱️ Interval: `{time_interval}s`
✉️ Mode: `{'Forward' if use_forward else 'Send'}`

> 🔄 _Running in background..._
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, starting_text, advertising_menu_keyboard())
    
    asyncio.create_task(run_advertising(user_id, context, accounts, ad_text, time_interval, use_forward))

async def run_advertising(user_id, context, accounts, ad_text, time_interval, use_forward):
    while context.user_data.get("advertising_active", False):
        for account in accounts:
            if not context.user_data.get("advertising_active", False):
                break
            
            try:
                user = await database.get_user(user_id)
                target_mode = user.get('target_mode', 'all') if user else 'all'
                
                if target_mode == "selected":
                    target_groups = await database.get_target_groups(user_id)
                    if target_groups:
                        for tg in target_groups:
                            if not context.user_data.get("advertising_active", False):
                                break
                            
                            if use_forward:
                                save_result = await telethon_handler.save_message_to_saved(account['_id'], ad_text)
                                if save_result["success"]:
                                    await telethon_handler.forward_message_to_chat(
                                        account['_id'],
                                        tg['group_id'],
                                        None,
                                        save_result["message_id"]
                                    )
                            else:
                                await telethon_handler.send_message_to_chat(
                                    account['_id'],
                                    tg['group_id'],
                                    ad_text
                                )
                            
                            await asyncio.sleep(time_interval)
                else:
                    result = await telethon_handler.broadcast_message(
                        account['_id'],
                        ad_text,
                        delay=time_interval,
                        use_forward=use_forward
                    )
                    
                    if not result["success"]:
                        logger.error(f"Broadcast failed for account {account['_id']}: {result.get('error')}")
                
            except Exception as e:
                logger.error(f"Advertising error: {e}")
            
            await asyncio.sleep(5)
        
        await asyncio.sleep(time_interval)

async def handle_otp_input(query, user_id, data, context):
    if user_id not in user_states:
        await send_new_message(query, "❌ Session expired. Please start again.", main_menu_keyboard())
        return
    
    state = user_states[user_id]
    
    if state["state"] != "awaiting_otp":
        return
    
    otp_code = state["data"].get("otp_code", "")
    
    if data == "otp_delete":
        otp_code = otp_code[:-1]
        state["data"]["otp_code"] = otp_code
        
        display_otp = otp_code if otp_code else "_ _ _ _ _"
        otp_text = f"""
🔐 *ᴇɴᴛᴇʀ ᴏᴛᴘ*

━━━━━━━━━━━━━━━━━━
📱 Code: `{display_otp}`

> _Use buttons below:_
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, otp_text, otp_keyboard())
    
    elif data == "otp_submit":
        if len(otp_code) < 5:
            await query.answer("OTP must be at least 5 digits!", show_alert=True)
            return
        
        await send_new_message(query, "⏳ *Verifying...*", None)
        
        api_id = state["data"]["api_id"]
        api_hash = state["data"]["api_hash"]
        phone = state["data"]["phone"]
        phone_code_hash = state["data"]["phone_code_hash"]
        session_string = state["data"]["session_string"]
        account_id = state["data"]["account_id"]
        
        result = await telethon_handler.verify_code(
            api_id, api_hash, phone, otp_code, phone_code_hash, session_string
        )
        
        if result["success"]:
            encrypted_session = encrypt_data(result["session_string"])
            
            info = await telethon_handler.get_account_info(api_id, api_hash, result["session_string"])
            
            profile_result = await telethon_handler.apply_profile_changes(api_id, api_hash, result["session_string"])
            if profile_result["success"]:
                encrypted_session = encrypt_data(profile_result["session_string"])
            
            await database.update_account(
                account_id,
                session_string=encrypted_session,
                is_logged_in=True,
                account_first_name=info.get("first_name") if info["success"] else None,
                account_username=info.get("username") if info["success"] else None
            )
            
            del user_states[user_id]
            
            success_text = f"""
✅ *ʟᴏɢɪɴ sᴜᴄᴄᴇssғᴜʟ*

━━━━━━━━━━━━━━━━━━
📱 Phone: `{phone}`
👤 Name: `{info.get('first_name', 'N/A')}`

> ✨ _Profile updated with bot settings!_
━━━━━━━━━━━━━━━━━━
"""
            await send_new_message(query, success_text, accounts_menu_keyboard())
        
        elif result.get("requires_2fa"):
            state["state"] = "awaiting_2fa"
            state["data"]["session_string"] = result["session_string"]
            
            twofa_text = """
🔐 *2ғᴀ ʀᴇǫᴜɪʀᴇᴅ*

━━━━━━━━━━━━━━━━━━
> _Enter your 2FA password:_

💡 Type your password and send.
━━━━━━━━━━━━━━━━━━
"""
            await send_new_message(query, twofa_text, twofa_keyboard())
        
        else:
            error_text = f"""
❌ *ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ғᴀɪʟᴇᴅ*

━━━━━━━━━━━━━━━━━━
⚠️ `{result['error']}`
━━━━━━━━━━━━━━━━━━
"""
            state["data"]["otp_code"] = ""
            await send_new_message(query, error_text, otp_keyboard())
    
    elif data == "otp_cancel":
        if user_id in user_states:
            del user_states[user_id]
        await send_new_message(query, "❌ *Cancelled.*", accounts_menu_keyboard())
    
    else:
        digit = data.split("_")[1]
        otp_code += digit
        state["data"]["otp_code"] = otp_code
        
        display_otp = otp_code if otp_code else "_ _ _ _ _"
        otp_text = f"""
🔐 *ᴇɴᴛᴇʀ ᴏᴛᴘ*

━━━━━━━━━━━━━━━━━━
📱 Code: `{display_otp}`

> _Use buttons below:_
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, otp_text, otp_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if config.ADMIN_ONLY_MODE and not is_admin(user_id):
        return
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    current_state = state["state"]
    
    if current_state == "awaiting_api_id":
        try:
            api_id = int(text.strip())
            state["data"]["api_id"] = str(api_id)
            state["state"] = "awaiting_api_hash"
            
            await update.message.reply_text(
                "📱 *ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ*\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "📍 *Step 2/4:* Enter your `API Hash`\n"
                "━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
                reply_markup=back_to_menu_keyboard()
            )
        except ValueError:
            await update.message.reply_text(
                "❌ *Invalid API ID*\n\n> _Please enter a valid number._",
                parse_mode="Markdown",
                reply_markup=back_to_menu_keyboard()
            )
    
    elif current_state == "awaiting_api_hash":
        api_hash = text.strip()
        state["data"]["api_hash"] = api_hash
        state["state"] = "awaiting_phone"
        
        await update.message.reply_text(
            "📱 *ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📍 *Step 3/4:* Enter phone number\n\n"
            "> 💡 Format: `+1234567890`\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard()
        )
    
    elif current_state == "awaiting_phone":
        phone = text.strip()
        if not phone.startswith("+"):
            phone = "+" + phone
        
        state["data"]["phone"] = phone
        
        await update.message.reply_text("⏳ *Sending OTP...*", parse_mode="Markdown")
        
        api_id = state["data"]["api_id"]
        api_hash = state["data"]["api_hash"]
        
        result = await telethon_handler.send_code(api_id, api_hash, phone)
        
        if result["success"]:
            encrypted_api_id = encrypt_data(api_id)
            encrypted_api_hash = encrypt_data(api_hash)
            
            account = await database.create_account(
                user_id=user_id,
                phone=phone,
                api_id=encrypted_api_id,
                api_hash=encrypted_api_hash
            )
            
            state["data"]["phone_code_hash"] = result["phone_code_hash"]
            state["data"]["session_string"] = result["session_string"]
            state["data"]["account_id"] = account["_id"]
            state["data"]["otp_code"] = ""
            state["state"] = "awaiting_otp"
            
            await update.message.reply_text(
                "📱 *ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ*\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "📍 *Step 4/4:* Enter OTP\n\n"
                f"> 📱 OTP sent to `{phone}`\n"
                "━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
                reply_markup=otp_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ *ғᴀɪʟᴇᴅ*\n\n━━━━━━━━━━━━━━━━━━\n⚠️ `{result['error']}`\n━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
                reply_markup=back_to_menu_keyboard()
            )
            del user_states[user_id]
    
    elif current_state == "awaiting_2fa":
        password = text.strip()
        
        await update.message.reply_text("⏳ *Verifying 2FA...*", parse_mode="Markdown")
        
        api_id = state["data"]["api_id"]
        api_hash = state["data"]["api_hash"]
        session_string = state["data"]["session_string"]
        account_id = state["data"]["account_id"]
        phone = state["data"]["phone"]
        
        result = await telethon_handler.verify_2fa_password(api_id, api_hash, password, session_string)
        
        if result["success"]:
            encrypted_session = encrypt_data(result["session_string"])
            
            info = await telethon_handler.get_account_info(api_id, api_hash, result["session_string"])
            
            await database.update_account(
                account_id,
                session_string=encrypted_session,
                is_logged_in=True,
                account_first_name=info.get("first_name") if info["success"] else None,
                account_username=info.get("username") if info["success"] else None
            )
            
            del user_states[user_id]
            
            await update.message.reply_text(
                f"✅ *ʟᴏɢɪɴ sᴜᴄᴄᴇssғᴜʟ*\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📱 Phone: `{phone}`\n"
                f"👤 Name: `{info.get('first_name', 'N/A')}`\n\n"
                f"> ✨ _Profile updated!_\n"
                f"━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
                reply_markup=accounts_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ *2ғᴀ ғᴀɪʟᴇᴅ*\n\n━━━━━━━━━━━━━━━━━━\n⚠️ `{result['error']}`\n\n> _Try again:_\n━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
                reply_markup=twofa_keyboard()
            )
    
    elif current_state == "awaiting_ad_text":
        ad_text = text.strip()
        await database.update_user(user_id, ad_text=ad_text)
        del user_states[user_id]
        
        await update.message.reply_text(
            "✅ *ᴀᴅ ᴛᴇxᴛ sᴀᴠᴇᴅ*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📝 Your ad text has been saved.\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=ad_text_menu_keyboard()
        )
    
    elif current_state == "awaiting_custom_time":
        try:
            seconds = int(text.strip())
            if seconds < 10:
                seconds = 10
            
            await database.update_user(user_id, time_interval=seconds)
            del user_states[user_id]
            
            await update.message.reply_text(
                f"✅ *ᴛɪᴍᴇ sᴇᴛ*\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ Interval: `{seconds}` seconds\n"
                f"━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
                reply_markup=advertising_menu_keyboard()
            )
        except ValueError:
            await update.message.reply_text(
                "❌ *Invalid*\n\n> _Enter a valid number._",
                parse_mode="Markdown",
                reply_markup=back_to_menu_keyboard()
            )
    
    elif current_state == "awaiting_target_group_id":
        try:
            group_id = int(text.strip())
            added = await database.add_target_group(user_id, group_id)
            del user_states[user_id]
            
            if added:
                await update.message.reply_text(
                    f"✅ *ɢʀᴏᴜᴘ ᴀᴅᴅᴇᴅ*\n\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👥 Group ID: `{group_id}`\n"
                    f"━━━━━━━━━━━━━━━━━━",
                    parse_mode="Markdown",
                    reply_markup=selected_groups_keyboard()
                )
            else:
                await update.message.reply_text(
                    "⚠️ *Already Added*\n\n> _This group is already in your list._",
                    parse_mode="Markdown",
                    reply_markup=selected_groups_keyboard()
                )
        except ValueError:
            await update.message.reply_text(
                "❌ *Invalid*\n\n> _Enter a valid Group ID._",
                parse_mode="Markdown",
                reply_markup=back_to_menu_keyboard()
            )
