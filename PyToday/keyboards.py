from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Advertising", callback_data="advertising_menu"),
         InlineKeyboardButton("👤 Accounts", callback_data="accounts_menu")],
        [InlineKeyboardButton("📂 Load GCs/MPs", callback_data="load_groups"),
         InlineKeyboardButton("📝 Set Ad Text", callback_data="set_ad_text")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("💬 Support", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def advertising_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚀 Start Advertising", callback_data="start_advertising")],
        [InlineKeyboardButton("🛑 Stop Advertising", callback_data="stop_advertising")],
        [InlineKeyboardButton("⏱️ Set Time", callback_data="set_time")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def accounts_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Account", callback_data="add_account")],
        [InlineKeyboardButton("🗑️ Delete Account", callback_data="delete_account")],
        [InlineKeyboardButton("📋 My Accounts", callback_data="my_accounts")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def support_keyboard():
    keyboard = [
        [InlineKeyboardButton("👨‍💻 Admin", url="https://t.me/dojutso")],
        [InlineKeyboardButton("📖 How to Use", url="https://t.me/dojutso")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_keyboard(use_multiple=False, use_forward=False, auto_reply=False, auto_group_join=False):
    forward_status = "🟢 ON" if use_forward else "🔴 OFF"
    forward_mode = "Forward" if use_forward else "Send"
    auto_reply_status = "🟢 ON" if auto_reply else "🔴 OFF"
    auto_join_status = "🟢 ON" if auto_group_join else "🔴 OFF"
    
    keyboard = [
        [InlineKeyboardButton("📱 Single Account", callback_data="single_mode"),
         InlineKeyboardButton("📱📱 Multiple Accounts", callback_data="multiple_mode")],
        [InlineKeyboardButton("📊 Statistics", callback_data="statistics")],
        [InlineKeyboardButton(f"✉️ Direct {forward_mode} [{forward_status}]", callback_data="toggle_forward_mode")],
        [InlineKeyboardButton(f"💬 Auto Reply [{auto_reply_status}]", callback_data="auto_reply_menu")],
        [InlineKeyboardButton(f"🔗 Auto Group Join [{auto_join_status}]", callback_data="toggle_auto_group_join")],
        [InlineKeyboardButton("🎯 Targeting", callback_data="target_adv")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def auto_reply_settings_keyboard(auto_reply_enabled=False):
    status = "🟢 ON" if auto_reply_enabled else "🔴 OFF"
    toggle_text = "🔴 Turn OFF" if auto_reply_enabled else "🟢 Turn ON"
    
    keyboard = [
        [InlineKeyboardButton(f"{toggle_text}", callback_data="toggle_auto_reply")],
        [InlineKeyboardButton("📝 Set Default Text", callback_data="set_default_reply")],
        [InlineKeyboardButton("➕ Add Reply Text", callback_data="add_reply_text")],
        [InlineKeyboardButton("🗑️ Delete Text", callback_data="delete_reply_text")],
        [InlineKeyboardButton("👁️ View Text", callback_data="view_reply_text")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def target_adv_keyboard(target_mode="all"):
    all_check = "✅" if target_mode == "all" else "⬜"
    selected_check = "✅" if target_mode == "selected" else "⬜"
    
    keyboard = [
        [InlineKeyboardButton(f"{all_check} All Groups", callback_data="target_all_groups")],
        [InlineKeyboardButton(f"{selected_check} Selected Groups", callback_data="target_selected_groups")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def selected_groups_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Group", callback_data="add_target_group")],
        [InlineKeyboardButton("➖ Remove Group", callback_data="remove_target_group")],
        [InlineKeyboardButton("🗑️ Clear All", callback_data="clear_target_groups")],
        [InlineKeyboardButton("📋 View Groups", callback_data="view_target_groups")],
        [InlineKeyboardButton("🔙 Back", callback_data="target_adv")]
    ]
    return InlineKeyboardMarkup(keyboard)

def otp_keyboard():
    keyboard = [
        [InlineKeyboardButton("1️⃣", callback_data="otp_1"),
         InlineKeyboardButton("2️⃣", callback_data="otp_2"),
         InlineKeyboardButton("3️⃣", callback_data="otp_3")],
        [InlineKeyboardButton("4️⃣", callback_data="otp_4"),
         InlineKeyboardButton("5️⃣", callback_data="otp_5"),
         InlineKeyboardButton("6️⃣", callback_data="otp_6")],
        [InlineKeyboardButton("7️⃣", callback_data="otp_7"),
         InlineKeyboardButton("8️⃣", callback_data="otp_8"),
         InlineKeyboardButton("9️⃣", callback_data="otp_9")],
        [InlineKeyboardButton("⬅️ Delete", callback_data="otp_delete"),
         InlineKeyboardButton("0️⃣", callback_data="otp_0"),
         InlineKeyboardButton("✅ Submit", callback_data="otp_submit")],
        [InlineKeyboardButton("❌ Cancel", callback_data="otp_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def twofa_keyboard():
    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="twofa_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def accounts_keyboard(accounts, page=0, per_page=5):
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_accounts = accounts[start:end]
    
    for acc in page_accounts:
        status = "🟢" if acc.get('is_logged_in') else "🔴"
        display_name = acc.get('account_first_name') or acc.get('phone', 'Unknown')
        if acc.get('account_username'):
            display_name = f"{display_name} (@{acc.get('account_username')})"
        keyboard.append([InlineKeyboardButton(
            f"{status} {display_name[:35]}", 
            callback_data=f"select_acc_{acc.get('_id')}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"acc_page_{page-1}"))
    if end < len(accounts):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"acc_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="accounts_menu")])
    return InlineKeyboardMarkup(keyboard)

def groups_keyboard(groups, account_id, page=0, per_page=10):
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_groups = groups[start:end]
    
    for grp in page_groups:
        title = grp.get('title', 'Unknown')[:30]
        grp_type = "🏪" if grp.get('is_marketplace') else "👥"
        keyboard.append([InlineKeyboardButton(
            f"{grp_type} {title}", 
            callback_data=f"group_info_{grp.get('id', 0)}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"grp_page_{account_id}_{page-1}"))
    if end < len(groups):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"grp_page_{account_id}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"load_grp_{account_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def delete_accounts_keyboard(accounts, page=0, per_page=5):
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_accounts = accounts[start:end]
    
    for acc in page_accounts:
        display_name = acc.get('account_first_name') or acc.get('phone', 'Unknown')
        if acc.get('account_username'):
            display_name = f"{display_name} (@{acc.get('account_username')})"
        keyboard.append([InlineKeyboardButton(
            f"🗑️ {display_name[:35]}", 
            callback_data=f"del_acc_{acc.get('_id')}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"del_page_{page-1}"))
    if end < len(accounts):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"del_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="accounts_menu")])
    return InlineKeyboardMarkup(keyboard)

def confirm_delete_keyboard(account_id):
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_del_{account_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data="delete_account")]
    ]
    return InlineKeyboardMarkup(keyboard)

def time_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏱️ 30 sec", callback_data="time_30"),
         InlineKeyboardButton("⏱️ 1 min", callback_data="time_60"),
         InlineKeyboardButton("⏱️ 2 min", callback_data="time_120")],
        [InlineKeyboardButton("⏱️ 5 min", callback_data="time_300"),
         InlineKeyboardButton("⏱️ 10 min", callback_data="time_600"),
         InlineKeyboardButton("⏱️ 15 min", callback_data="time_900")],
        [InlineKeyboardButton("⏱️ 30 min", callback_data="time_1800"),
         InlineKeyboardButton("⏱️ 1 hour", callback_data="time_3600"),
         InlineKeyboardButton("⚙️ Custom", callback_data="time_custom")],
        [InlineKeyboardButton("🔙 Back", callback_data="advertising_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_menu_keyboard():
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)

def back_to_settings_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="settings")]]
    return InlineKeyboardMarkup(keyboard)

def back_to_auto_reply_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="auto_reply_menu")]]
    return InlineKeyboardMarkup(keyboard)

def ad_text_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📄 Saved Text", callback_data="ad_saved_text")],
        [InlineKeyboardButton("➕ Add Text", callback_data="ad_add_text")],
        [InlineKeyboardButton("🗑️ Delete Text", callback_data="ad_delete_text")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def ad_text_back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="set_ad_text")]]
    return InlineKeyboardMarkup(keyboard)

def account_selection_keyboard(accounts, selected_ids=None, page=0, per_page=5):
    if selected_ids is None:
        selected_ids = []
    
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_accounts = accounts[start:end]
    
    for acc in page_accounts:
        if acc.get('is_logged_in'):
            is_selected = str(acc.get('_id')) in [str(s) for s in selected_ids]
            check = "✅" if is_selected else "⬜"
            display_name = acc.get('account_first_name') or acc.get('phone', 'Unknown')
            if acc.get('account_username'):
                display_name = f"{display_name} (@{acc.get('account_username')})"
            keyboard.append([InlineKeyboardButton(
                f"{check} {display_name[:35]}", 
                callback_data=f"toggle_acc_{acc.get('_id')}"
            )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"sel_page_{page-1}"))
    if end < len(accounts):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"sel_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("✅ Confirm Selection", callback_data="confirm_selection")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="settings")])
    return InlineKeyboardMarkup(keyboard)

def target_groups_list_keyboard(groups, page=0, per_page=5):
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_groups = groups[start:end]
    
    for grp in page_groups:
        title = grp.get('group_title', str(grp.get('group_id', 'Unknown')))[:30]
        keyboard.append([InlineKeyboardButton(
            f"👥 {title}", 
            callback_data=f"tg_info_{grp.get('group_id', 0)}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"tg_page_{page-1}"))
    if end < len(groups):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"tg_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="target_selected_groups")])
    return InlineKeyboardMarkup(keyboard)

def remove_groups_keyboard(groups, page=0, per_page=5):
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_groups = groups[start:end]
    
    for grp in page_groups:
        title = grp.get('group_title', str(grp.get('group_id', 'Unknown')))[:25]
        keyboard.append([InlineKeyboardButton(
            f"🗑️ {title}", 
            callback_data=f"rm_tg_{grp.get('group_id', 0)}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"rmtg_page_{page-1}"))
    if end < len(groups):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"rmtg_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="target_selected_groups")])
    return InlineKeyboardMarkup(keyboard)

def single_account_selection_keyboard(accounts, page=0, per_page=5):
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_accounts = accounts[start:end]
    
    for acc in page_accounts:
        display_name = acc.get('account_first_name') or acc.get('phone', 'Unknown')
        if acc.get('account_username'):
            display_name = f"{display_name} (@{acc.get('account_username')})"
        keyboard.append([InlineKeyboardButton(
            f"📱 {display_name[:35]}", 
            callback_data=f"select_single_{acc.get('_id')}"
        )])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"single_page_{page-1}"))
    if end < len(accounts):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"single_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="settings")])
    return InlineKeyboardMarkup(keyboard)
