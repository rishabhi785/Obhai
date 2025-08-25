import asyncio
import json
import os
import random
import string
import aiohttp
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Bot configuration
BOT_TOKEN = "8309249310:AAFTxV4I7dDqUlmldGY3UGw07E8meqSq0I8"
CHANNEL_LINK = "https://t.me/freepromochannels"
GROUP_LINK = "https://t.me/viralam"
CHANNEL_ID = -1002729077216
GROUP_ID = -1002879269738
SUPPORT_USERNAME = "@zerixem"
WEBAPP_URL = "https://row-vert.vercel.app"
ADMIN_ID = "6736711885" # Your admin chat ID

# Backend verification URL
BACKEND_URL = "https://9d4f4c9d-ffeb-441c-8677-be836689e54d-00-2c2givkv2clmi.pike.replit.dev/verify"

# VSV API Configuration
VSV_API_URL = "https://vsv-gateway-solutions.co.in/Api/api.php"
VSV_API_TOKEN = "RKMDLSMZ"

# Data files
USERS_FILE = "users_data.json"
REDEEM_CODES_FILE = "redeem_codes.json"
CONFIG_FILE = "config.json"
CHANNELS_FILE = "channels_data.json"

# Default configuration
DEFAULT_CONFIG = {
    "min_withdrawal": 1,
    "daily_bonus": 1,
    "referral_bonus": 2
}

# Global variables for admin channel management
user_states = {}
WAITING_FOR_CHANNEL = "waiting_for_channel"
WAITING_FOR_CHANNEL_REMOVE = "waiting_for_channel_remove"
WAITING_FOR_BROADCAST = "waiting_for_broadcast"
WAITING_FOR_CHANNEL_POST = "waiting_for_channel_post"

# Load configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Load additional channels
def load_extra_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('extra_channels', [])
    return []

def save_extra_channels(channels):
    data = {'extra_channels': channels}
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Load data functions
def load_users_data():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users_data(data):
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_redeem_codes():
    if os.path.exists(REDEEM_CODES_FILE):
        with open(REDEEM_CODES_FILE, 'r') as f:
            return json.load(f)
    return ["1A6ZNVNDNYX842UE", "9Z99FF2XM1N46AT5"]

def save_redeem_codes(codes):
    with open(REDEEM_CODES_FILE, 'w') as f:
        json.dump(codes, f, indent=2)

def generate_fake_redeem_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

# Global data
users_data = load_users_data()
redeem_codes = load_redeem_codes()
config = load_config()
extra_channels = load_extra_channels()

# Helper function to extract channel ID from link
def extract_channel_id_from_link(link):
    patterns = [
        r't\.me/([a-zA-Z0-9_]+)',
        r'telegram\.me/([a-zA-Z0-9_]+)',
        r'@([a-zA-Z0-9_]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return f"@{match.group(1)}"
    return None

# Validate channel/group function
async def validate_channel(context, channel_link):
    try:
        channel_username = extract_channel_id_from_link(channel_link)
        if not channel_username:
            return {"valid": False, "error": "Invalid channel link format"}
        chat = await context.bot.get_chat(channel_username)
        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status not in ['administrator', 'member']:
                return {"valid": False, "error": "Bot is not a member of this channel"}
        except Exception:
            return {"valid": False, "error": "Bot doesn't have access to this channel"}
        return {
            "valid": True,
            "chat_id": chat.id,
            "title": chat.title,
            "type": chat.type,
            "username": channel_username
        }
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}

def validate_wallet_number(wallet_number):
    return bool(re.match(r'^\d{10}$', wallet_number))

# VSV API integration
async def transfer_money_via_vsv(recipient_wallet, amount, user_id):
    try:
        comment = f"Bot_Withdrawal_User_{user_id}"
        api_url = f"{VSV_API_URL}?token={VSV_API_TOKEN}&paytm={recipient_wallet}&amount={amount}&comment={comment}"
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    result = await response.text()
                    print(f"VSV API Response: {result}")
                    try:
                        json_response = json.loads(result)
                        if isinstance(json_response, dict) and 'status' in json_response:
                            if json_response['status'].lower() == 'success':
                                return {'success': True, 'transaction_id': f'VSV_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'}
                            else:
                                error_msg = json_response.get('message', 'Transfer failed')
                                return {'success': False, 'error': f'{error_msg}'}
                    except json.JSONDecodeError:
                        pass
                    if "success" in result.lower() or "completed" in result.lower() or "sent" in result.lower():
                        return {'success': True, 'transaction_id': f'VSV_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'}
                    else:
                        return {'success': False, 'error': f'Transfer failed: {result}'}
                else:
                    error_data = await response.text()
                    return {'success': False, 'error': f'API Error: {response.status} - {error_data}'}
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Transfer timeout - please try again later'}
    except Exception as e:
        return {'success': False, 'error': f'Transfer failed: {str(e)}'}

async def check_membership(context, user_id):
    try:
        channel_task = context.bot.get_chat_member(CHANNEL_ID, user_id)
        group_task = context.bot.get_chat_member(GROUP_ID, user_id)
        extra_tasks = []
        for channel in extra_channels:
            task = context.bot.get_chat_member(channel["id"], user_id)
            extra_tasks.append(task)
        all_tasks = [channel_task, group_task] + extra_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                print(f"Membership check failed: {result}")
                return True
            if result.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        print(f"Membership check error: {e}")
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"
    if context.args:
        referrer_id = context.args[0]
        if referrer_id != user_id and referrer_id in users_data:
            if user_id not in users_data:
                users_data[referrer_id]["balance"] += config["referral_bonus"]
                users_data[referrer_id]["referrals"] += 1
                save_users_data(users_data)
                await context.bot.send_message(referrer_id, f"*🎉 You earned ₹{config['referral_bonus']} from a new referral!*", parse_mode="Markdown")
    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 0,
            "referrals": 0,
            "last_bonus": None,
            "joined_channels": False,
            "verified": False,
            "wallet_number": None
        }
        save_users_data(users_data)
    is_member = await check_membership(context, user_id)
    users_data[user_id]["joined_channels"] = is_member
    save_users_data(users_data)
    if is_member and users_data[user_id].get("verified", False):
        await show_main_menu(update, context)
    else:
        keyboard = []
        keyboard.append([InlineKeyboardButton("Join", url=CHANNEL_LINK),
                         InlineKeyboardButton("Join", url=GROUP_LINK)])
        for i in range(0, len(extra_channels), 2):
            row = []
            for j in range(i, min(i + 2, len(extra_channels))):
                channel = extra_channels[j]
                row.append(InlineKeyboardButton("Join", url=channel["link"]))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔒claim", callback_data="claim")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"*😍 Hi {username} Welcome To Bot*\n\n*🟢 Must Join All Channels To Use Bot*\n\n◼️ *After Joining Click '🔒claim'*"
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

#=== 1. ADD THIS FUNCTION FOR BACKEND DEVICE VERIFICATION ===#
async def verify_device_with_backend(user_id, web_app_data):
    """Device verification backend API se"""
    try:
        device_data = json.loads(web_app_data)  # webapp ka data (string) ko parse karo
        payload = {
            'user_id': user_id,
            'device_data': device_data
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(BACKEND_URL, json=payload) as response:
                return await response.json()
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
#============================================================#

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = str(update.effective_user.id)
    if user_id == ADMIN_ID:
        keyboard = [
            ["BALANCE", "REFERAL LINK"],
            ["BONUS", "WITHDRAW"],
            ["LINK WALLET"],
            ["🔧 ADMIN PANEL"]
        ]
    else:
        keyboard = [
            ["BALANCE", "REFERAL LINK"],
            ["BONUS", "WITHDRAW"],
            ["LINK WALLET"]
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    text = "*🏠 Welcome! Use buttons below to manage your account.*"
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            await update.callback_query.answer()
        elif hasattr(update, 'web_app_data') and update.web_app_data:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error showing menu: {e}")
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as fallback_error:
            print(f"Fallback error: {fallback_error}")

async def show_delayed_main_menu(chat_id: int, username: str, context: ContextTypes.DEFAULT_TYPE):
    try:
        await asyncio.sleep(8)
        if chat_id == int(ADMIN_ID):
            keyboard = [
                ["BALANCE", "REFERAL LINK"],
                ["BONUS", "WITHDRAW"],
                ["LINK WALLET"],
                ["🔧 ADMIN PANEL"]
            ]
        else:
            keyboard = [
                ["BALANCE", "REFERAL LINK"],
                ["BONUS", "WITHDRAW"],
                ["LINK WALLET"]
            ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        main_menu_text = f"*🏠 WELCOME {username} AND EARN MONEY EASILY*"
        await context.bot.send_message(
            chat_id=chat_id,
            text=main_menu_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        print(f"Main menu sent successfully to user {username}")
    except Exception as e:
        print(f"Error in delayed main menu: {e}")
        try:
            if chat_id == int(ADMIN_ID):
                keyboard = [
                    ["BALANCE", "REFERAL LINK"],
                    ["BONUS", "WITHDRAW"],
                    ["LINK WALLET"],
                    ["🔧 ADMIN PANEL"]
                ]
            else:
                keyboard = [
                    ["BALANCE", "REFERAL LINK"],
                    ["BONUS", "WITHDRAW"],
                    ["LINK WALLET"]
                ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*🏠 WELCOME {username} AND EARN MONEY EASILY*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as fallback_error:
            print(f"Fallback error in delayed main menu: {fallback_error}")

async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    username = query.from_user.first_name or "User"
    try:
        await query.answer("✅ Processing...")
    except Exception as e:
        print(f"Error answering callback query: {e}")
    if users_data[user_id].get("verified", False) and users_data[user_id].get("joined_channels", False):
        print(f"User {user_id} already verified, showing delayed main menu instantly")
        await show_delayed_main_menu(query.message.chat_id, username, context)
        return
    try:
        is_member = await asyncio.wait_for(check_membership(context, user_id), timeout=1.0)
        if is_member:
            users_data[user_id]["joined_channels"] = True
            save_users_data(users_data)
            webapp_button = InlineKeyboardButton("✅ Verify", web_app=WebAppInfo(url=WEBAPP_URL))
            keyboard = [[webapp_button]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"*✅ Thanks {username}! Now click 'Verify' button below to complete verification.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            asyncio.create_task(show_delayed_main_menu(query.message.chat_id, username, context))
        else:
            keyboard = []
            keyboard.append([InlineKeyboardButton("Join", url=CHANNEL_LINK),
                             InlineKeyboardButton("Join", url=GROUP_LINK)])
            for i in range(0, len(extra_channels), 2):
                row = []
                for j in range(i, min(i + 2, len(extra_channels))):
                    channel = extra_channels[j]
                    row.append(InlineKeyboardButton("Join", url=channel["link"]))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🔒claim", callback_data="claim")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = f"*{username}, please join both channel and group first!*\n\n*After joining, click '✨claim' again.*"
            try:
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            except Exception as e:
                print(f"Message edit failed: {e}")
                await context.bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode="Markdown")
    except asyncio.TimeoutError:
        print(f"Membership check timeout for user {user_id}")
        await query.edit_message_text(
            text="*⏰ Verification taking longer than expected. Please try again in a moment.*",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error in claim callback: {e}")
        await query.edit_message_text(
            text="*❌ Error during verification. Please try again.*",
            parse_mode="Markdown"
        )

#============= 2. REPLACE THIS HANDLER: WEB APP DATA VERIFICATION =============#
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"
    chat_id = update.effective_chat.id
    try:
        # Backend par device verification bhejo
        verification_result = await verify_device_with_backend(user_id, update.web_app_data.data)
        if verification_result.get('status') == 'success':
            if user_id not in users_data:
                users_data[user_id] = {
                    "balance": 0,
                    "referrals": 0,
                    "last_bonus": None,
                    "joined_channels": True,
                    "verified": True,
                    "wallet_number": None
                }
            else:
                users_data[user_id]["verified"] = True
                users_data[user_id]["joined_channels"] = True
            save_users_data(users_data)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*✅ Device verification successful!* \n\nWelcome {username}! Ab aap sab features use kar sakte ho.",
                parse_mode="Markdown"
            )
            await show_delayed_main_menu(chat_id, username, context)
        else:
            error_msg = verification_result.get('message', 'Verification failed')
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*❌ Verification Failed*\n\nReason: {error_msg}",
                parse_mode="Markdown"
            )
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text="*❌ Verification error! Try /start again*",
            parse_mode="Markdown"
        )
#===============================================================================#

# ------- rest of your message handler, admin panels, wallet, withdraw, bonus etc functions go below -------
# (No other change is required in the remaining code. Saare command, callback & menu, admin panel jese pehle hi work karenge.)

# .... [Rest of the code remains unchanged: handle_message, handle_bonus, handle_withdraw_request, etc.] ....

def main():
    print("Bot is starting...")
    save_config(config)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    print("Bot started successfully!")
    application.run_polling()

if __name__ == "__main__":
    main()
