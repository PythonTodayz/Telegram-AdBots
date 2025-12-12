import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from telegram.constants import ParseMode
from PyToday import *

logger = logging.getLogger(__name__)
user_states = {}

WELCOME_TEXT_TEMPLATE = """
<b>◈ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴅ ʙᴏᴛ ◈</b>

<blockquote>▸ <b>ᴡᴇʟᴄᴏᴍᴇ,</b> <code>{first_name}</code>
▸ <b>ᴜsᴇʀs:</b> <code>{total_users}</code></blockquote>

<blockquote expandable>» ᴀᴜᴛᴏ ᴀᴅᴠᴇʀᴛɪsɪɴɢ
» ᴀᴜᴛᴏ ʀᴇᴘʟʏ ᴛᴏ ᴅᴍs
» ᴀᴜᴛᴏ ɢʀᴏᴜᴘ ᴊᴏɪɴ
» sᴛᴀᴛɪsᴛɪᴄs ᴛʀᴀᴄᴋɪɴɢ
» ᴍᴜʟᴛɪ-ᴀᴄᴄᴏᴜɴᴛ sᴜᴘᴘᴏʀᴛ
» sᴄʜᴇᴅᴜʟᴇᴅ sᴇɴᴅɪɴɢ</blockquote>

<i>sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ:</i>
"""

MENU_TEXT_TEMPLATE = """
<b>◈ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴅ ʙᴏᴛ ◈</b>

━━━━━━━━━━━━━━━━━━
<blockquote>◉ <b>ᴛᴏᴛᴀʟ ᴜsᴇʀs:</b> <code>{total_users}</code></blockquote>
━━━━━━━━━━━━━━━━━━

<i>sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ:</i>
"""

async def safe_edit_message(query, text, parse_mode="HTML", reply_markup=None):
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Failed to edit message: {e}")

async def safe_edit_caption(query, text, parse_mode="HTML", reply_markup=None):
    try:
        await query.edit_message_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Failed to edit caption: {e}")

async def send_notification(query, text, reply_markup=None):
    try:
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
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
<b>⊘ ᴘʀɪᴠᴀᴛᴇ ʙᴏᴛ</b>

<blockquote><i>ᴛʜɪs ʙᴏᴛ ɪs ғᴏʀ ᴘᴇʀsᴏɴᴀʟ ᴜsᴇ ᴏɴʟʏ.</i>
<i>ᴄᴏɴᴛᴀᴄᴛ ᴛʜᴇ ᴀᴅᴍɪɴ ғᴏʀ ᴀᴄᴄᴇss.</i></blockquote>

◈ <a href="tg://user?id=7756391784">ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ</a>
"""
        try:
            await update.message.reply_photo(
                photo=config.START_IMAGE_URL,
                caption=private_text,
                has_spoiler = True,
	            message_effect_id=5104841245755180586 #🔥
                parse_mode="HTML"
            )
        except:
            await update.message.reply_text(private_text, parse_mode="HTML")
        return
    
    total_users = await database.get_bot_users_count()
    
    welcome_text = WELCOME_TEXT_TEMPLATE.format(
        first_name=user.first_name,
        total_users=total_users
    )
    
    context.user_data['welcome_text'] = welcome_text
    context.user_data['first_name'] = user.first_name
    
    try:
        await update.message.reply_photo(
            photo=config.START_IMAGE_URL,
            caption=welcome_text,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to send photo: {e}")
        await update.message.reply_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("<b>⊘ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴀᴅᴍɪɴs.</b>", parse_mode="HTML")
        return
    
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            "<b>◈ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴍᴀɴᴅ</b>\n\n"
            "<blockquote>ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ ᴏʀ sᴇɴᴅ:\n"
            "<code>/broadcast Your message here</code></blockquote>\n\n"
            "<i>sᴜᴘᴘᴏʀᴛs: ᴛᴇxᴛ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, ᴅᴏᴄᴜᴍᴇɴᴛ, ᴀᴜᴅɪᴏ</i>",
            parse_mode="HTML"
        )
        return
    
    user_states[user.id] = {"state": "broadcasting", "data": {}}
    
    all_users = await database.get_all_bot_users()
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text(
        f"<b>▸ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...</b>\n\n"
        f"◉ ᴛᴏᴛᴀʟ: <code>{len(all_users)}</code>\n"
        f"● sᴇɴᴛ: <code>0</code>\n"
        f"○ ғᴀɪʟᴇᴅ: <code>0</code>",
        parse_mode="HTML"
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
                        parse_mode="HTML"
                    )
                elif reply_msg.video:
                    await context.bot.send_video(
                        bot_user["_id"],
                        reply_msg.video.file_id,
                        caption=reply_msg.caption,
                        parse_mode="HTML"
                    )
                elif reply_msg.document:
                    await context.bot.send_document(
                        bot_user["_id"],
                        reply_msg.document.file_id,
                        caption=reply_msg.caption,
                        parse_mode="HTML"
                    )
                elif reply_msg.audio:
                    await context.bot.send_audio(
                        bot_user["_id"],
                        reply_msg.audio.file_id,
                        caption=reply_msg.caption,
                        parse_mode="HTML"
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
                        parse_mode="HTML"
                    )
            else:
                text = " ".join(context.args)
                await context.bot.send_message(
                    bot_user["_id"],
                    text,
                    parse_mode="HTML"
                )
            sent += 1
        except Exception as e:
            logger.error(f"Broadcast failed for {bot_user['_id']}: {e}")
            failed += 1
        
        if (sent + failed) % 10 == 0:
            try:
                await status_msg.edit_text(
                    f"<b>▸ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...</b>\n\n"
                    f"◉ ᴛᴏᴛᴀʟ: <code>{len(all_users)}</code>\n"
                    f"● sᴇɴᴛ: <code>{sent}</code>\n"
                    f"○ ғᴀɪʟᴇᴅ: <code>{failed}</code>",
                    parse_mode="HTML"
                )
            except:
                pass
        
        await asyncio.sleep(0.05)
    
    if user.id in user_states:
        del user_states[user.id]
    
    await status_msg.edit_text(
        f"<b>✓ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ</b>\n\n"
        f"◉ ᴛᴏᴛᴀʟ: <code>{len(all_users)}</code>\n"
        f"● sᴇɴᴛ: <code>{sent}</code>\n"
        f"○ ғᴀɪʟᴇᴅ: <code>{failed}</code>",
        parse_mode="HTML"
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
        await send_new_message(query, "<b>✕ 2ғᴀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>\n\n<blockquote><i>ʀᴇᴛᴜʀɴɪɴɢ ᴛᴏ ᴍᴀɪɴ ᴍᴇɴᴜ...</i></blockquote>", main_menu_keyboard())
        return
    
    if data == "main_menu":
        await show_main_menu(query, context)
    
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
    
    elif data == "auto_reply_menu":
        await show_auto_reply_menu(query, user_id)
    
    elif data == "toggle_auto_reply":
        await toggle_auto_reply(query, user_id)
    
    elif data == "set_default_reply":
        await set_default_reply_text(query, user_id)
    
    elif data == "add_reply_text":
        await prompt_add_reply_text(query, user_id)
    
    elif data == "delete_reply_text":
        await delete_reply_text(query, user_id)
    
    elif data == "view_reply_text":
        await view_reply_text(query, user_id)
    
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
            "<b>▣ ᴀᴅᴠᴇʀᴛɪsɪɴɢ sᴛᴏᴘᴘᴇᴅ</b>\n\n<blockquote>✓ <i>ʏᴏᴜʀ ᴄᴀᴍᴘᴀɪɢɴ ʜᴀs ʙᴇᴇɴ sᴛᴏᴘᴘᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.</i></blockquote>",
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
        has_media = query.message.photo or query.message.document or query.message.video
        
        if has_media:
            try:
                await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=reply_markup)
                return
            except BadRequest as e:
                error_msg = str(e)
                if "Message is not modified" in error_msg:
                    return
                logger.warning(f"Caption edit failed: {e}")
                return
        
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")
        try:
            await query.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as ex:
            logger.error(f"Failed to send reply: {ex}")

async def show_main_menu(query, context=None):
    if user_states.get(query.from_user.id):
        del user_states[query.from_user.id]
    
    total_users = await database.get_bot_users_count()
    first_name = query.from_user.first_name
    
    if context and context.user_data.get('first_name'):
        first_name = context.user_data.get('first_name')
    
    menu_text = WELCOME_TEXT_TEMPLATE.format(
        first_name=first_name,
        total_users=total_users
    )
    
    await send_new_message(query, menu_text, main_menu_keyboard())

async def show_advertising_menu(query):
    adv_text = """
<b>◈ ᴀᴅᴠᴇʀᴛɪsɪɴɢ ᴍᴇɴᴜ</b>

━━━━━━━━━━━━━━━━━━
<blockquote>» <b>sᴛᴀʀᴛ</b> - ʙᴇɢɪɴ ᴀᴅᴠᴇʀᴛɪsɪɴɢ
▣ <b>sᴛᴏᴘ</b> - sᴛᴏᴘ ᴀᴅᴠᴇʀᴛɪsɪɴɢ
◴ <b>sᴇᴛ ᴛɪᴍᴇ</b> - ᴄʜᴀɴɢᴇ ɪɴᴛᴇʀᴠᴀʟ</blockquote>
━━━━━━━━━━━━━━━━━━

<i>sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ:</i>
"""
    await send_new_message(query, adv_text, advertising_menu_keyboard())

async def show_accounts_menu(query):
    acc_text = """
<b>◈ ᴀᴄᴄᴏᴜɴᴛs ᴍᴇɴᴜ</b>

━━━━━━━━━━━━━━━━━━
<blockquote>＋ <b>ᴀᴅᴅ</b> - ᴀᴅᴅ ɴᴇᴡ ᴀᴄᴄᴏᴜɴᴛ
✕ <b>ᴅᴇʟᴇᴛᴇ</b> - ʀᴇᴍᴏᴠᴇ ᴀᴄᴄᴏᴜɴᴛ
≡ <b>ᴍʏ ᴀᴄᴄᴏᴜɴᴛs</b> - ᴠɪᴇᴡ ᴀʟʟ</blockquote>
━━━━━━━━━━━━━━━━━━

<i>sᴇʟᴇᴄᴛ ᴀɴ ᴏᴘᴛɪᴏɴ:</i>
"""
    await send_new_message(query, acc_text, accounts_menu_keyboard())

async def show_support(query):
    support_text = """
<b>💬 sᴜᴘᴘᴏʀᴛ & ʜᴇʟᴘ ᴄᴇɴᴛᴇʀ</b>

━━━━━━━━━━━━━━━━━━
<blockquote><b>🆘 Need Assistance?</b>
We're here to help you 24/7!</blockquote>

<b>📌 Quick Help:</b>
<blockquote>• <b>Getting Started:</b> Add your Telegram account first
• <b>API Credentials:</b> Get from my.telegram.org
• <b>Auto Reply:</b> Enable in Settings to auto-respond
• <b>Advertising:</b> Set ad text, then start campaign</blockquote>

<b>📞 Contact Options:</b>
<blockquote>• <b>Admin Support:</b> Direct help from developer
• <b>Tutorial:</b> Step-by-step guide to use bot</blockquote>

<b>⚠️ Common Issues:</b>
<blockquote>• Session expired? Re-login your account
• OTP not received? Check Telegram app
• 2FA required? Enter your cloud password</blockquote>
━━━━━━━━━━━━━━━━━━
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
<b>⚙️ sᴇᴛᴛɪɴɢs</b>

━━━━━━━━━━━━━━━━━━
<b>📊 Current Configuration:</b>

<blockquote>🔹 <b>Account Mode:</b> {mode_text}
🔹 <b>Message Mode:</b> {forward_text}
🔹 <b>Auto Reply:</b> {auto_reply_text}
🔹 <b>Auto Join:</b> {auto_join_text}</blockquote>
━━━━━━━━━━━━━━━━━━

<i>Tap to change settings:</i>
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
        mode_text = "<b>✉️ ғᴏʀᴡᴀʀᴅ ᴍᴏᴅᴇ</b>"
        description = "<blockquote><i>Messages will be forwarded from Saved Messages with premium emojis preserved</i></blockquote>"
        icon = "🟢"
    else:
        mode_text = "<b>📤 sᴇɴᴅ ᴍᴏᴅᴇ</b>"
        description = "<blockquote><i>Messages will be sent directly</i></blockquote>"
        icon = "🔴"
    
    result_text = f"""
{icon} <b>ᴍᴏᴅᴇ ᴄʜᴀɴɢᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
✅ Changed to: {mode_text}

{description}
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, settings_keyboard(use_multiple, new_mode, auto_reply, auto_group_join))

async def show_auto_reply_menu(query, user_id):
    user = await database.get_user(user_id)
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    reply_text = user.get('auto_reply_text', '') if user else ''
    is_custom = bool(reply_text)
    
    status = "🟢 ON" if auto_reply else "🔴 OFF"
    text_type = "Custom" if is_custom else "Default"
    
    menu_text = f"""
<b>💬 ᴀᴜᴛᴏ ʀᴇᴘʟʏ sᴇᴛᴛɪɴɢs</b>

━━━━━━━━━━━━━━━━━━
<b>📊 Current Configuration:</b>

<blockquote>🔹 <b>Status:</b> {status}
🔹 <b>Text Type:</b> {text_type}</blockquote>
━━━━━━━━━━━━━━━━━━

<i>Manage your auto-reply settings:</i>
"""
    
    await send_new_message(query, menu_text, auto_reply_settings_keyboard(auto_reply))

async def toggle_auto_reply(query, user_id):
    user = await database.get_user(user_id)
    current_mode = user.get('auto_reply_enabled', False) if user else False
    new_mode = not current_mode
    
    await database.update_user(user_id, auto_reply_enabled=new_mode)
    
    user = await database.get_user(user_id)
    reply_text = user.get('auto_reply_text', '') if user else ''
    final_text = reply_text if reply_text else config.AUTO_REPLY_TEXT
    
    if new_mode:
        started = await telethon_handler.start_all_auto_reply_listeners(user_id, final_text)
        status_detail = f"Started for {started} account(s)"
    else:
        stopped = await telethon_handler.stop_all_auto_reply_listeners(user_id)
        status_detail = f"Stopped for {stopped} account(s)"
    
    status = "🟢 ON" if new_mode else "🔴 OFF"
    is_custom = bool(reply_text)
    text_type = "Custom" if is_custom else "Default"
    
    result_text = f"""
<b>💬 ᴀᴜᴛᴏ ʀᴇᴘʟʏ</b>

━━━━━━━━━━━━━━━━━━
✅ Auto Reply is now: <b>{status}</b>
📊 {status_detail}

<blockquote>🔹 <b>Text Type:</b> {text_type}</blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, auto_reply_settings_keyboard(new_mode))

async def set_default_reply_text(query, user_id):
    await database.update_user(user_id, auto_reply_text='')
    
    user = await database.get_user(user_id)
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    
    if auto_reply:
        await telethon_handler.start_all_auto_reply_listeners(user_id, config.AUTO_REPLY_TEXT)
    
    result_text = f"""
<b>📝 ᴅᴇғᴀᴜʟᴛ ᴛᴇxᴛ sᴇᴛ</b>

━━━━━━━━━━━━━━━━━━
✅ Now using default reply text:

<blockquote>{config.AUTO_REPLY_TEXT}</blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, auto_reply_settings_keyboard(auto_reply))

async def prompt_add_reply_text(query, user_id):
    user_states[user_id] = {"state": "awaiting_reply_text"}
    
    prompt_text = """
<b>➕ ᴀᴅᴅ ʀᴇᴘʟʏ ᴛᴇxᴛ</b>

━━━━━━━━━━━━━━━━━━
📝 <b>Send your custom auto-reply text:</b>

<blockquote><i>This message will be sent automatically when someone DMs your account.</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, prompt_text, back_to_auto_reply_keyboard())

async def delete_reply_text(query, user_id):
    user = await database.get_user(user_id)
    current_text = user.get('auto_reply_text', '') if user else ''
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    
    if not current_text:
        result_text = """
<b>❌ ɴᴏ ᴄᴜsᴛᴏᴍ ᴛᴇxᴛ</b>

━━━━━━━━━━━━━━━━━━
<blockquote><i>You don't have any custom reply text set. Using default text.</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    else:
        await database.update_user(user_id, auto_reply_text='')
        
        if auto_reply:
            await telethon_handler.start_all_auto_reply_listeners(user_id, config.AUTO_REPLY_TEXT)
        
        result_text = """
<b>🗑️ ᴛᴇxᴛ ᴅᴇʟᴇᴛᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
✅ Custom reply text has been deleted.

<blockquote><i>Now using default text.</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, auto_reply_settings_keyboard(auto_reply))

async def view_reply_text(query, user_id):
    user = await database.get_user(user_id)
    custom_text = user.get('auto_reply_text', '') if user else ''
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    
    if custom_text:
        text_type = "Custom"
        display_text = custom_text
    else:
        text_type = "Default"
        display_text = config.AUTO_REPLY_TEXT
    
    result_text = f"""
<b>👁️ ᴄᴜʀʀᴇɴᴛ ʀᴇᴘʟʏ ᴛᴇxᴛ</b>

━━━━━━━━━━━━━━━━━━
<b>📊 Type:</b> {text_type}

<b>📝 Text:</b>
<blockquote>{display_text}</blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, auto_reply_settings_keyboard(auto_reply))

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
<b>🔗 ᴀᴜᴛᴏ ɢʀᴏᴜᴘ ᴊᴏɪɴ</b>

━━━━━━━━━━━━━━━━━━
✅ Auto Join is now: <b>{status}</b>

<blockquote><i>When enabled, accounts will auto-join groups from links</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, settings_keyboard(use_multiple, use_forward, auto_reply, new_mode))

async def show_target_adv(query, user_id):
    user = await database.get_user(user_id)
    target_mode = user.get('target_mode', 'all') if user else 'all'
    
    target_text = f"""
<b>🎯 ᴛᴀʀɢᴇᴛ ᴀᴅᴠᴇʀᴛɪsɪɴɢ</b>

━━━━━━━━━━━━━━━━━━
<b>📊 Current Mode:</b> <code>{target_mode.upper()}</code>

<blockquote>📢 <b>All Groups</b> - Send to all groups
🎯 <b>Selected</b> - Send to specific groups</blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, target_text, target_adv_keyboard(target_mode))

async def set_target_all_groups(query, user_id):
    await database.update_user(user_id, target_mode="all")
    
    result_text = """
<b>✅ ᴛᴀʀɢᴇᴛ sᴇᴛ</b>

━━━━━━━━━━━━━━━━━━
📢 Target Mode: <b>ALL GROUPS</b>

<blockquote><i>Messages will be sent to all groups</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, target_adv_keyboard("all"))

async def show_selected_groups_menu(query, user_id):
    await database.update_user(user_id, target_mode="selected")
    
    target_groups = await database.get_target_groups(user_id)
    
    menu_text = f"""
<b>🎯 sᴇʟᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘs</b>

━━━━━━━━━━━━━━━━━━
<b>📊 Selected Groups:</b> <code>{len(target_groups)}</code>

<blockquote>➕ Add groups by ID
➖ Remove groups
📋 View all selected</blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, menu_text, selected_groups_keyboard())

async def prompt_add_target_group(query, user_id):
    user_states[user_id] = {"state": "awaiting_target_group_id", "data": {}}
    
    prompt_text = """
<b>➕ ᴀᴅᴅ ɢʀᴏᴜᴘ</b>

━━━━━━━━━━━━━━━━━━
<blockquote><i>Send the Group ID to add:</i></blockquote>

<b>💡 How to get Group ID:</b>
Forward a message from the group to @userinfobot
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, prompt_text, back_to_menu_keyboard())

async def remove_target_group(query, user_id, group_id):
    removed = await database.remove_target_group(user_id, group_id)
    
    if removed:
        result_text = f"""
<b>✅ ɢʀᴏᴜᴘ ʀᴇᴍᴏᴠᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
🗑️ Group <code>{group_id}</code> removed successfully.
━━━━━━━━━━━━━━━━━━
"""
    else:
        result_text = f"""
<b>❌ ᴇʀʀᴏʀ</b>

━━━━━━━━━━━━━━━━━━
Group <code>{group_id}</code> not found.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, selected_groups_keyboard())

async def show_remove_target_groups(query, user_id, page=0):
    target_groups = await database.get_target_groups(user_id)
    
    if not target_groups:
        await send_new_message(
            query,
            "<b>❌ No groups to remove</b>\n\n<blockquote><i>Add some groups first.</i></blockquote>",
            selected_groups_keyboard()
        )
        return
    
    await send_new_message(
        query,
        "<b>🗑️ Select a group to remove:</b>",
        remove_groups_keyboard(target_groups, page)
    )

async def clear_all_target_groups(query, user_id):
    count = await database.clear_target_groups(user_id)
    
    result_text = f"""
<b>🗑️ ɢʀᴏᴜᴘs ᴄʟᴇᴀʀᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
✅ Removed <code>{count}</code> groups from target list.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, selected_groups_keyboard())

async def view_target_groups(query, user_id, page=0):
    target_groups = await database.get_target_groups(user_id)
    
    if not target_groups:
        await send_new_message(
            query,
            "<b>📋 No targeted groups</b>\n\n<blockquote><i>Add groups to target them.</i></blockquote>",
            selected_groups_keyboard()
        )
        return
    
    await send_new_message(
        query,
        f"<b>📋 Targeted Groups ({len(target_groups)})</b>",
        target_groups_list_keyboard(target_groups, page)
    )

async def start_add_account(query, user_id):
    user_states[user_id] = {"state": "awaiting_api_id", "data": {}}
    
    prompt_text = """
<b>➕ ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ</b>

━━━━━━━━━━━━━━━━━━
<b>Step 1/4:</b> Send your <b>API ID</b>

<blockquote>Get it from: <a href="https://my.telegram.org">my.telegram.org</a></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, prompt_text, back_to_menu_keyboard())

async def show_delete_accounts(query, user_id, page=0):
    accounts = await database.get_accounts(user_id)
    
    if not accounts:
        await send_new_message(
            query,
            "<b>❌ No accounts to delete</b>\n\n<blockquote><i>Add an account first.</i></blockquote>",
            accounts_menu_keyboard()
        )
        return
    
    await send_new_message(
        query,
        "<b>🗑️ Select an account to delete:</b>",
        delete_accounts_keyboard(accounts, page)
    )

async def confirm_delete_account(query, account_id):
    account = await database.get_account(account_id)
    
    if not account:
        await send_new_message(
            query,
            "<b>❌ Account not found</b>",
            accounts_menu_keyboard()
        )
        return
    
    display_name = account.get('account_first_name') or account.get('phone', 'Unknown')
    
    confirm_text = f"""
<b>⚠️ ᴄᴏɴғɪʀᴍ ᴅᴇʟᴇᴛᴇ</b>

━━━━━━━━━━━━━━━━━━
Are you sure you want to delete:
<b>{display_name}</b>?

<blockquote><i>This action cannot be undone.</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, confirm_text, confirm_delete_keyboard(account_id))

async def delete_account(query, user_id, account_id):
    deleted = await database.delete_account(account_id, user_id)
    
    if deleted:
        result_text = """
<b>✅ ᴀᴄᴄᴏᴜɴᴛ ᴅᴇʟᴇᴛᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
Account removed successfully.
━━━━━━━━━━━━━━━━━━
"""
    else:
        result_text = """
<b>❌ ᴇʀʀᴏʀ</b>

━━━━━━━━━━━━━━━━━━
Failed to delete account.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, accounts_menu_keyboard())

async def load_groups(query, user_id):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if not accounts:
        await send_new_message(
            query,
            "<b>❌ No logged in accounts</b>\n\n<blockquote><i>Please add and login to an account first.</i></blockquote>",
            main_menu_keyboard()
        )
        return
    
    if len(accounts) == 1:
        account = accounts[0]
        account_id = str(account["_id"])
        
        await send_new_message(
            query,
            "<b>⏳ Loading groups...</b>\n\n<blockquote><i>Please wait while we fetch your groups and marketplaces.</i></blockquote>",
            None
        )
        
        result = await telethon_handler.get_groups_and_marketplaces(account_id)
        
        if not result["success"]:
            await send_new_message(
                query,
                f"<b>❌ Error loading groups</b>\n\n{result.get('error', 'Unknown error')}",
                main_menu_keyboard()
            )
            return
        
        all_chats = result["groups"] + result["marketplaces"]
        
        groups_text = f"""
<b>📂 ɢʀᴏᴜᴘs & ᴍᴀʀᴋᴇᴛᴘʟᴀᴄᴇs</b>

━━━━━━━━━━━━━━━━━━
<blockquote>👥 <b>Groups:</b> <code>{len(result['groups'])}</code>
🏪 <b>Marketplaces:</b> <code>{len(result['marketplaces'])}</code>
📊 <b>Total:</b> <code>{result['total']}</code></blockquote>
━━━━━━━━━━━━━━━━━━
"""
        
        await send_new_message(query, groups_text, groups_keyboard(all_chats, account_id))
    else:
        await send_new_message(
            query,
            "<b>📂 Select an account to load groups:</b>",
            single_account_selection_keyboard([acc for acc in accounts if acc.get('is_logged_in')])
        )

async def load_account_groups(query, user_id, account_id, context):
    await send_new_message(
        query,
        "<b>⏳ Loading groups...</b>\n\n<blockquote><i>Please wait...</i></blockquote>",
        None
    )
    
    result = await telethon_handler.get_groups_and_marketplaces(account_id)
    
    if not result["success"]:
        await send_new_message(
            query,
            f"<b>❌ Error loading groups</b>\n\n{result.get('error', 'Unknown error')}",
            main_menu_keyboard()
        )
        return
    
    all_chats = result["groups"] + result["marketplaces"]
    context.user_data[f"groups_{account_id}"] = all_chats
    
    groups_text = f"""
<b>📂 ɢʀᴏᴜᴘs & ᴍᴀʀᴋᴇᴛᴘʟᴀᴄᴇs</b>

━━━━━━━━━━━━━━━━━━
<blockquote>👥 <b>Groups:</b> <code>{len(result['groups'])}</code>
🏪 <b>Marketplaces:</b> <code>{len(result['marketplaces'])}</code>
📊 <b>Total:</b> <code>{result['total']}</code></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, groups_text, groups_keyboard(all_chats, account_id))

async def load_account_groups_page(query, user_id, account_id, page, context):
    all_chats = context.user_data.get(f"groups_{account_id}", [])
    
    if not all_chats:
        result = await telethon_handler.get_groups_and_marketplaces(account_id)
        if result["success"]:
            all_chats = result["groups"] + result["marketplaces"]
            context.user_data[f"groups_{account_id}"] = all_chats
    
    await send_new_message(
        query,
        f"<b>📂 Groups (Page {page + 1})</b>",
        groups_keyboard(all_chats, account_id, page)
    )

async def show_statistics(query, user_id):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if not accounts:
        stats_text = """
<b>📊 sᴛᴀᴛɪsᴛɪᴄs</b>

━━━━━━━━━━━━━━━━━━
<blockquote><i>No accounts found. Add an account first.</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
        await send_new_message(query, stats_text, back_to_settings_keyboard())
        return
    
    stats_text = "<b>📊 ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ sᴛᴀᴛɪsᴛɪᴄs</b>\n\n"
    
    for account in accounts:
        display_name = account.get('account_first_name') or account.get('phone', 'Unknown')
        if account.get('account_username'):
            display_name = f"{display_name} (@{account.get('account_username')})"
        
        stats = await database.get_account_stats(account["_id"])
        
        if stats:
            sent = stats.get("messages_sent", 0)
            failed = stats.get("messages_failed", 0)
            groups = stats.get("groups_count", 0) + stats.get("marketplaces_count", 0)
            replies = stats.get("auto_replies_sent", 0)
            joined = stats.get("groups_joined", 0)
        else:
            sent = failed = groups = replies = joined = 0
        
        stats_text += f"""━━━━━━━━━━━━━━━━━━
<b>📱 {display_name[:30]}</b>
<blockquote>✅ Sent: <code>{sent}</code> | ❌ Failed: <code>{failed}</code>
👥 Groups: <code>{groups}</code> | 💬 Replies: <code>{replies}</code>
🔗 Joined: <code>{joined}</code></blockquote>
"""
    
    stats_text += f"""━━━━━━━━━━━━━━━━━━
<b>📱 Total Accounts:</b> <code>{len(accounts)}</code>
"""
    
    await send_new_message(query, stats_text, back_to_settings_keyboard())

async def show_ad_text_menu(query, user_id):
    user = await database.get_user(user_id)
    ad_text = user.get('ad_text') if user else None
    ad_status = "✅ Set" if ad_text else "❌ Not Set"
    
    menu_text = f"""
<b>📝 ᴀᴅ ᴛᴇxᴛ ᴍᴇɴᴜ</b>

━━━━━━━━━━━━━━━━━━
<blockquote>📝 <b>Ad Text:</b> {ad_status}</blockquote>
━━━━━━━━━━━━━━━━━━

<i>Select an option:</i>
"""
    
    await send_new_message(query, menu_text, ad_text_menu_keyboard())

async def show_saved_ad_text(query, user_id):
    user = await database.get_user(user_id)
    ad_text = user.get('ad_text') if user else None
    
    if ad_text:
        display_text = f"""
<b>📄 sᴀᴠᴇᴅ ᴀᴅ ᴛᴇxᴛ</b>

━━━━━━━━━━━━━━━━━━
<blockquote>{ad_text[:500]}{'...' if len(ad_text) > 500 else ''}</blockquote>
━━━━━━━━━━━━━━━━━━
"""
    else:
        display_text = """
<b>📄 sᴀᴠᴇᴅ ᴀᴅ ᴛᴇxᴛ</b>

━━━━━━━━━━━━━━━━━━
<blockquote><i>No ad text saved.</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, display_text, ad_text_back_keyboard())

async def prompt_ad_text(query, user_id):
    user_states[user_id] = {"state": "awaiting_ad_text", "data": {}}
    
    prompt_text = """
<b>➕ ᴀᴅᴅ ᴀᴅ ᴛᴇxᴛ</b>

━━━━━━━━━━━━━━━━━━
<blockquote><i>Send your ad text now:</i></blockquote>

<b>💡 Tips:</b>
• Use <code>&lt;b&gt;text&lt;/b&gt;</code> for <b>bold</b>
• Use <code>&lt;i&gt;text&lt;/i&gt;</code> for <i>italic</i>
• Use <code>&lt;blockquote&gt;text&lt;/blockquote&gt;</code> for quotes
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, prompt_text, ad_text_back_keyboard())

async def delete_ad_text(query, user_id):
    await database.update_user(user_id, ad_text=None)
    
    result_text = """
<b>🗑️ ᴀᴅ ᴛᴇxᴛ ᴅᴇʟᴇᴛᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
✅ Your ad text has been deleted.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, ad_text_menu_keyboard())

async def show_time_options(query):
    time_text = """
<b>⏱️ sᴇᴛ ᴛɪᴍᴇ ɪɴᴛᴇʀᴠᴀʟ</b>

━━━━━━━━━━━━━━━━━━
<blockquote><i>Select the delay between messages:</i></blockquote>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, time_text, time_keyboard())

async def set_time_interval(query, user_id, time_val):
    if time_val == "custom":
        user_states[user_id] = {"state": "awaiting_custom_time", "data": {}}
        await send_new_message(
            query,
            "<b>⚙️ Custom Time</b>\n\n<blockquote><i>Send the delay in seconds:</i></blockquote>",
            back_to_menu_keyboard()
        )
        return
    
    try:
        seconds = int(time_val)
        await database.update_user(user_id, time_interval=seconds)
        
        if seconds < 60:
            time_display = f"{seconds} seconds"
        elif seconds < 3600:
            time_display = f"{seconds // 60} minute(s)"
        else:
            time_display = f"{seconds // 3600} hour(s)"
        
        result_text = f"""
<b>✅ ᴛɪᴍᴇ sᴇᴛ</b>

━━━━━━━━━━━━━━━━━━
⏱️ Interval set to: <b>{time_display}</b>
━━━━━━━━━━━━━━━━━━
"""
        
        await send_new_message(query, result_text, advertising_menu_keyboard())
    except ValueError:
        await send_new_message(
            query,
            "<b>❌ Invalid time value</b>",
            time_keyboard()
        )

async def set_single_mode(query, user_id):
    await database.update_user(user_id, use_multiple_accounts=False)
    
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if not accounts:
        await send_new_message(
            query,
            "<b>❌ No logged in accounts</b>\n\n<blockquote><i>Please add an account first.</i></blockquote>",
            settings_keyboard(False, False, False, False)
        )
        return
    
    if len(accounts) == 1:
        result_text = """
<b>✅ sɪɴɢʟᴇ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴀᴛᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
📱 Using your only account for advertising.
━━━━━━━━━━━━━━━━━━
"""
        user = await database.get_user(user_id)
        use_forward = user.get('use_forward_mode', False) if user else False
        auto_reply = user.get('auto_reply_enabled', False) if user else False
        auto_group_join = user.get('auto_group_join_enabled', False) if user else False
        
        await send_new_message(query, result_text, settings_keyboard(False, use_forward, auto_reply, auto_group_join))
    else:
        await send_new_message(
            query,
            "<b>📱 Select an account for single mode:</b>",
            single_account_selection_keyboard(accounts)
        )

async def set_multiple_mode(query, user_id, context):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if len(accounts) < 2:
        await send_new_message(
            query,
            "<b>❌ Need at least 2 accounts</b>\n\n<blockquote><i>Add more accounts for multiple mode.</i></blockquote>",
            settings_keyboard(False, False, False, False)
        )
        return
    
    context.user_data["selected_accounts"] = []
    
    await send_new_message(
        query,
        "<b>📱📱 Select accounts for multiple mode:</b>",
        account_selection_keyboard(accounts, [])
    )

async def toggle_account_selection(query, user_id, account_id, context):
    selected = context.user_data.get("selected_accounts", [])
    
    if account_id in selected:
        selected.remove(account_id)
    else:
        selected.append(account_id)
    
    context.user_data["selected_accounts"] = selected
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    await send_new_message(
        query,
        f"<b>📱📱 Selected: {len(selected)} accounts</b>",
        account_selection_keyboard(accounts, selected)
    )

async def show_account_selection(query, user_id, page, context):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    selected = context.user_data.get("selected_accounts", [])
    
    await send_new_message(
        query,
        f"<b>📱📱 Selected: {len(selected)} accounts</b>",
        account_selection_keyboard(accounts, selected, page)
    )

async def confirm_account_selection(query, user_id, context):
    selected = context.user_data.get("selected_accounts", [])
    
    if len(selected) < 2:
        await send_new_message(
            query,
            "<b>❌ Select at least 2 accounts</b>",
            account_selection_keyboard(await database.get_accounts(user_id, logged_in_only=True), selected)
        )
        return
    
    await database.update_user(user_id, use_multiple_accounts=True, selected_accounts=selected)
    
    user = await database.get_user(user_id)
    use_forward = user.get('use_forward_mode', False) if user else False
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    auto_group_join = user.get('auto_group_join_enabled', False) if user else False
    
    result_text = f"""
<b>✅ ᴍᴜʟᴛɪᴘʟᴇ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴀᴛᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
📱📱 Using <b>{len(selected)}</b> accounts for advertising.
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, settings_keyboard(True, use_forward, auto_reply, auto_group_join))

async def show_my_accounts(query, user_id, page=0):
    accounts = await database.get_accounts(user_id)
    
    if not accounts:
        await send_new_message(
            query,
            "<b>📋 No accounts</b>\n\n<blockquote><i>Add an account to get started.</i></blockquote>",
            accounts_menu_keyboard()
        )
        return
    
    await send_new_message(
        query,
        f"<b>📋 Your Accounts ({len(accounts)})</b>",
        accounts_keyboard(accounts, page)
    )

async def select_single_account(query, user_id, account_id):
    await database.update_user(user_id, use_multiple_accounts=False, selected_single_account=account_id)
    
    account = await database.get_account(account_id)
    display_name = account.get('account_first_name', 'Unknown') if account else 'Unknown'
    
    user = await database.get_user(user_id)
    use_forward = user.get('use_forward_mode', False) if user else False
    auto_reply = user.get('auto_reply_enabled', False) if user else False
    auto_group_join = user.get('auto_group_join_enabled', False) if user else False
    
    result_text = f"""
<b>✅ ᴀᴄᴄᴏᴜɴᴛ sᴇʟᴇᴄᴛᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
📱 Using: <b>{display_name}</b>
━━━━━━━━━━━━━━━━━━
"""
    
    await send_new_message(query, result_text, settings_keyboard(False, use_forward, auto_reply, auto_group_join))

async def show_single_account_page(query, user_id, page):
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    await send_new_message(
        query,
        "<b>📱 Select an account:</b>",
        single_account_selection_keyboard(accounts, page)
    )

async def start_advertising(query, user_id, context):
    user = await database.get_user(user_id)
    
    if not user:
        await send_new_message(
            query,
            "<b>❌ Error: User not found</b>",
            advertising_menu_keyboard()
        )
        return
    
    ad_text = user.get('ad_text')
    use_forward = user.get('use_forward_mode', False)
    use_multiple = user.get('use_multiple_accounts', False)
    time_interval = user.get('time_interval', 60)
    target_mode = user.get('target_mode', 'all')
    
    accounts = await database.get_accounts(user_id, logged_in_only=True)
    
    if not accounts:
        await send_new_message(
            query,
            "<b>❌ No logged in accounts</b>\n\n<blockquote><i>Please add and login to an account first.</i></blockquote>",
            advertising_menu_keyboard()
        )
        return
    
    if not use_forward and not ad_text:
        await send_new_message(
            query,
            "<b>❌ No ad text set</b>\n\n<blockquote><i>Please set your ad text first or enable forward mode to forward from Saved Messages.</i></blockquote>",
            advertising_menu_keyboard()
        )
        return
    
    if use_multiple:
        selected_accounts = user.get('selected_accounts', [])
        if not selected_accounts:
            selected_accounts = [str(acc["_id"]) for acc in accounts]
        active_accounts = [acc for acc in accounts if str(acc["_id"]) in selected_accounts]
    else:
        single_account = user.get('selected_single_account')
        if single_account:
            active_accounts = [acc for acc in accounts if str(acc["_id"]) == single_account]
        else:
            active_accounts = [accounts[0]] if accounts else []
    
    if not active_accounts:
        await send_new_message(
            query,
            "<b>❌ No accounts selected</b>\n\n<blockquote><i>Please select accounts in settings.</i></blockquote>",
            advertising_menu_keyboard()
        )
        return
    
    if target_mode == "selected":
        target_groups = await database.get_target_groups(user_id)
        if not target_groups:
            await send_new_message(
                query,
                "<b>❌ No target groups selected</b>\n\n<blockquote><i>Please add target groups in Targeting settings.</i></blockquote>",
                advertising_menu_keyboard()
            )
            return
    
    context.user_data["advertising_active"] = True
    
    mode_text = "Forward from Saved Messages" if use_forward else "Direct Send"
    target_text = f"Selected ({len(target_groups) if target_mode == 'selected' else 0} groups)" if target_mode == "selected" else "All Groups"
    
    start_text = f"""
<b>🚀 ᴀᴅᴠᴇʀᴛɪsɪɴɢ sᴛᴀʀᴛᴇᴅ</b>

━━━━━━━━━━━━━━━━━━
<blockquote>📱 <b>Accounts:</b> <code>{len(active_accounts)}</code>
✉️ <b>Mode:</b> <code>{mode_text}</code>
🎯 <b>Target:</b> <code>{target_text}</code>
⏱️ <b>Interval:</b> <code>{time_interval}s</code></blockquote>
━━━━━━━━━━━━━━━━━━

<i>Campaign is running...</i>
"""
    
    await send_new_message(query, start_text, advertising_menu_keyboard())
    
    asyncio.create_task(run_advertising_campaign(user_id, active_accounts, ad_text, time_interval, use_forward, target_mode, context))

async def run_advertising_campaign(user_id, accounts, ad_text, delay, use_forward, target_mode, context):
    try:
        while context.user_data.get("advertising_active", False):
            for account in accounts:
                if not context.user_data.get("advertising_active", False):
                    break
                
                account_id = str(account["_id"])
                
                if target_mode == "selected":
                    target_groups = await database.get_target_groups(user_id)
                    result = await telethon_handler.broadcast_to_target_groups(
                        account_id, target_groups, ad_text, delay, use_forward
                    )
                else:
                    result = await telethon_handler.broadcast_message(
                        account_id, ad_text, delay, use_forward
                    )
                
                if not context.user_data.get("advertising_active", False):
                    break
                
                await asyncio.sleep(delay)
    except Exception as e:
        logger.error(f"Advertising campaign error: {e}")

async def handle_otp_input(query, user_id, data, context):
    state = user_states.get(user_id, {})
    
    if state.get("state") != "awaiting_otp":
        return
    
    otp_code = state.get("data", {}).get("otp_code", "")
    
    action = data.replace("otp_", "")
    
    if action == "cancel":
        if user_id in user_states:
            del user_states[user_id]
        await send_new_message(query, "<b>❌ Login cancelled</b>", main_menu_keyboard())
        return
    
    if action == "delete":
        otp_code = otp_code[:-1]
        user_states[user_id]["data"]["otp_code"] = otp_code
        
        display = otp_code + "●" * (5 - len(otp_code))
        await send_new_message(
            query,
            f"<b>🔐 Enter OTP Code</b>\n\n<code>{display}</code>",
            otp_keyboard()
        )
        return
    
    if action == "submit":
        if len(otp_code) < 5:
            await query.answer("Please enter at least 5 digits", show_alert=True)
            return
        
        await send_new_message(query, "<b>⏳ Verifying code...</b>", None)
        
        account_data = state.get("data", {})
        api_id = account_data.get("api_id")
        api_hash = account_data.get("api_hash")
        phone = account_data.get("phone")
        phone_code_hash = account_data.get("phone_code_hash")
        session_string = account_data.get("session_string")
        
        result = await telethon_handler.verify_code(
            api_id, api_hash, phone, otp_code, phone_code_hash, session_string
        )
        
        if result["success"]:
            from PyToday.encryption import encrypt_data
            
            account = await database.create_account(
                user_id, phone,
                encrypt_data(str(api_id)),
                encrypt_data(api_hash)
            )
            
            await database.update_account(
                account["_id"],
                session_string=encrypt_data(result["session_string"]),
                is_logged_in=True
            )
            
            info = await telethon_handler.get_account_info(api_id, api_hash, result["session_string"])
            if info["success"]:
                await database.update_account(
                    account["_id"],
                    account_first_name=info["first_name"],
                    account_last_name=info["last_name"],
                    account_username=info["username"]
                )
            
            if user_id in user_states:
                del user_states[user_id]
            
            await send_new_message(
                query,
                "<b>✅ ᴀᴄᴄᴏᴜɴᴛ ᴀᴅᴅᴇᴅ</b>\n\n<blockquote><i>Account logged in successfully!</i></blockquote>",
                main_menu_keyboard()
            )
        elif result.get("requires_2fa"):
            user_states[user_id]["state"] = "awaiting_2fa"
            user_states[user_id]["data"]["session_string"] = result["session_string"]
            
            await send_new_message(
                query,
                "<b>🔐 2FA Required</b>\n\n<blockquote><i>Send your 2FA password:</i></blockquote>",
                twofa_keyboard()
            )
        else:
            await send_new_message(
                query,
                f"<b>❌ Error:</b> {result.get('error', 'Unknown error')}",
                otp_keyboard()
            )
        return
    
    if action.isdigit():
        if len(otp_code) < 6:
            otp_code += action
            user_states[user_id]["data"]["otp_code"] = otp_code
        
        display = otp_code + "●" * (5 - len(otp_code))
        await send_new_message(
            query,
            f"<b>🔐 Enter OTP Code</b>\n\n<code>{display}</code>",
            otp_keyboard()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    state = user_states.get(user_id, {})
    current_state = state.get("state")
    
    if not current_state:
        return
    
    if current_state == "awaiting_api_id":
        try:
            api_id = int(text)
            user_states[user_id]["data"]["api_id"] = api_id
            user_states[user_id]["state"] = "awaiting_api_hash"
            
            await update.message.reply_text(
                "<b>Step 2/4:</b> Send your <b>API Hash</b>",
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text(
                "<b>❌ Invalid API ID</b>\n\nPlease send a valid number.",
                parse_mode="HTML"
            )
    
    elif current_state == "awaiting_api_hash":
        user_states[user_id]["data"]["api_hash"] = text
        user_states[user_id]["state"] = "awaiting_phone"
        
        await update.message.reply_text(
            "<b>Step 3/4:</b> Send your <b>Phone Number</b>\n\n<blockquote>Format: +1234567890</blockquote>",
            parse_mode="HTML"
        )
    
    elif current_state == "awaiting_phone":
        phone = text.strip()
        if not phone.startswith("+"):
            phone = "+" + phone
        
        user_states[user_id]["data"]["phone"] = phone
        
        await update.message.reply_text(
            "<b>⏳ Sending OTP...</b>",
            parse_mode="HTML"
        )
        
        api_id = user_states[user_id]["data"]["api_id"]
        api_hash = user_states[user_id]["data"]["api_hash"]
        
        result = await telethon_handler.send_code(api_id, api_hash, phone)
        
        if result["success"]:
            user_states[user_id]["state"] = "awaiting_otp"
            user_states[user_id]["data"]["phone_code_hash"] = result["phone_code_hash"]
            user_states[user_id]["data"]["session_string"] = result["session_string"]
            user_states[user_id]["data"]["otp_code"] = ""
            
            await update.message.reply_text(
                "<b>🔐 Enter OTP Code</b>\n\n<code>●●●●●</code>",
                parse_mode="HTML",
                reply_markup=otp_keyboard()
            )
        else:
            await update.message.reply_text(
                f"<b>❌ Error:</b> {result.get('error', 'Unknown error')}",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
            if user_id in user_states:
                del user_states[user_id]
    
    elif current_state == "awaiting_2fa":
        password = text
        
        await update.message.reply_text(
            "<b>⏳ Verifying 2FA...</b>",
            parse_mode="HTML"
        )
        
        api_id = user_states[user_id]["data"]["api_id"]
        api_hash = user_states[user_id]["data"]["api_hash"]
        phone = user_states[user_id]["data"]["phone"]
        session_string = user_states[user_id]["data"]["session_string"]
        
        result = await telethon_handler.verify_2fa_password(api_id, api_hash, password, session_string)
        
        if result["success"]:
            from PyToday.encryption import encrypt_data
            
            account = await database.create_account(
                user_id, phone,
                encrypt_data(str(api_id)),
                encrypt_data(api_hash)
            )
            
            await database.update_account(
                account["_id"],
                session_string=encrypt_data(result["session_string"]),
                is_logged_in=True
            )
            
            info = await telethon_handler.get_account_info(api_id, api_hash, result["session_string"])
            if info["success"]:
                await database.update_account(
                    account["_id"],
                    account_first_name=info["first_name"],
                    account_last_name=info["last_name"],
                    account_username=info["username"]
                )
            
            if user_id in user_states:
                del user_states[user_id]
            
            await update.message.reply_text(
                "<b>✅ ᴀᴄᴄᴏᴜɴᴛ ᴀᴅᴅᴇᴅ</b>\n\n<blockquote><i>Account logged in successfully!</i></blockquote>",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                f"<b>❌ Error:</b> {result.get('error', 'Unknown error')}",
                parse_mode="HTML",
                reply_markup=twofa_keyboard()
            )
    
    elif current_state == "awaiting_ad_text":
        await database.update_user(user_id, ad_text=text)
        
        if user_id in user_states:
            del user_states[user_id]
        
        await update.message.reply_text(
            "<b>✅ ᴀᴅ ᴛᴇxᴛ sᴀᴠᴇᴅ</b>\n\n<blockquote><i>Your ad text has been saved.</i></blockquote>",
            parse_mode="HTML",
            reply_markup=ad_text_menu_keyboard()
        )
    
    elif current_state == "awaiting_reply_text":
        await database.update_user(user_id, auto_reply_text=text)
        
        user = await database.get_user(user_id)
        auto_reply = user.get('auto_reply_enabled', False) if user else False
        
        if auto_reply:
            await telethon_handler.start_all_auto_reply_listeners(user_id, text)
        
        if user_id in user_states:
            del user_states[user_id]
        
        await update.message.reply_text(
            "<b>✅ ʀᴇᴘʟʏ ᴛᴇxᴛ sᴀᴠᴇᴅ</b>\n\n<blockquote><i>Your custom auto-reply text has been saved.</i></blockquote>",
            parse_mode="HTML",
            reply_markup=auto_reply_settings_keyboard(auto_reply)
        )
    
    elif current_state == "awaiting_custom_time":
        try:
            seconds = int(text)
            if seconds < 10:
                await update.message.reply_text(
                    "<b>❌ Time must be at least 10 seconds</b>",
                    parse_mode="HTML"
                )
                return
            
            await database.update_user(user_id, time_interval=seconds)
            
            if user_id in user_states:
                del user_states[user_id]
            
            await update.message.reply_text(
                f"<b>✅ Time set to {seconds} seconds</b>",
                parse_mode="HTML",
                reply_markup=advertising_menu_keyboard()
            )
        except ValueError:
            await update.message.reply_text(
                "<b>❌ Please send a valid number</b>",
                parse_mode="HTML"
            )
    
    elif current_state == "awaiting_target_group_id":
        try:
            group_id = int(text.strip().replace("-100", "-100"))
            
            added = await database.add_target_group(user_id, group_id, f"Group {group_id}")
            
            if user_id in user_states:
                del user_states[user_id]
            
            if added:
                await update.message.reply_text(
                    f"<b>✅ Group added</b>\n\nGroup ID: <code>{group_id}</code>",
                    parse_mode="HTML",
                    reply_markup=selected_groups_keyboard()
                )
            else:
                await update.message.reply_text(
                    "<b>⚠️ Group already in list</b>",
                    parse_mode="HTML",
                    reply_markup=selected_groups_keyboard()
                )
        except ValueError:
            await update.message.reply_text(
                "<b>❌ Invalid Group ID</b>\n\nPlease send a valid number.",
                parse_mode="HTML"
            )
