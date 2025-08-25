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
BOT_TOKEN = "8050193229:AAFfRAytczD85MtOV9_bxzBk305gR7kc2NM"
CHANNEL_LINK = "https://t.me/freepromochannels"
GROUP_LINK = "https://t.me/viralam"
CHANNEL_ID = -1002729077216
GROUP_ID = -1002879269738
SUPPORT_USERNAME = "@zerixem"
WEBAPP_URL = "https://veryfyhtml.netlify.app/"
BACKEND_URL = "https://9d4f4c9d-ffeb-441c-8677-be836689e54d-00-2c2givkv2clmi.pike.replit.dev"
ADMIN_ID = "6736711885"  # Your admin chat ID

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
    """Extract channel username from Telegram link"""
    patterns = [
        r't\.me/([a-zA-Z0-9_]+)',
        r'telegram\.me/([a-zA-Z0-9_]+)',  # Fixed: 0d9 -> 0-9
        r'@([a-zA-Z0-9_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return f"@{match.group(1)}"
    
    return None

# Validate channel/group function
async def validate_channel(context, channel_link):
    """Validate if channel exists and bot has access"""
    try:
        channel_username = extract_channel_id_from_link(channel_link)
        if not channel_username:
            return {"valid": False, "error": "Invalid channel link format"}
        
        # Try to get chat information
        chat = await context.bot.get_chat(channel_username)
        
        # Check if bot is member/admin
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

# Wallet validation function
def validate_wallet_number(wallet_number):
    """Validate VSV wallet number (must be 10 digits)"""
    return bool(re.match(r'^\d{10}$', wallet_number))

# VSV API integration
async def transfer_money_via_vsv(recipient_wallet, amount, user_id):
    """Transfer money using VSV API"""
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
        # Check default channels
        channel_task = context.bot.get_chat_member(CHANNEL_ID, user_id)
        group_task = context.bot.get_chat_member(GROUP_ID, user_id)
        
        # Check extra channels
        extra_tasks = []
        for channel in extra_channels:
            task = context.bot.get_chat_member(channel["id"], user_id)
            extra_tasks.append(task)
        
        # Wait for all checks
        all_tasks = [channel_task, group_task] + extra_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Check if all are valid responses and user is member
        for result in results:
            if isinstance(result, Exception):
                print(f"Membership check failed: {result}")
                return True  # Assume joined on API errors to avoid blocking users
            
            if result.status not in ['member', 'administrator', 'creator']:
                return False
                
        return True
    except Exception as e:
        print(f"Membership check error: {e}")
        return True  # Assume joined on errors

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"

    # Referral handling
    if context.args:
        referrer_id = context.args[0]
        if referrer_id != user_id and referrer_id in users_data:
            if user_id not in users_data:
                users_data[referrer_id]["balance"] += config["referral_bonus"]
                users_data[referrer_id]["referrals"] += 1
                save_users_data(users_data)
                await context.bot.send_message(referrer_id, f"*🎉 You earned ₹{config['referral_bonus']} from a new referral!*", parse_mode="Markdown")

    # Initialize user data
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

    # Check membership
    is_member = await check_membership(context, user_id)
    users_data[user_id]["joined_channels"] = is_member
    save_users_data(users_data)

    # Check if user is verified and member
    if is_member and users_data[user_id].get("verified", False):
        await show_main_menu(update, context)
    else:
        # Create dynamic keyboard with default + extra channels
        keyboard = []
        
        # Add default channels
        keyboard.append([InlineKeyboardButton("Join", url=CHANNEL_LINK),
                        InlineKeyboardButton("Join", url=GROUP_LINK)])
        
        # Add extra channels in rows of 2
        for i in range(0, len(extra_channels), 2):
            row = []
            for j in range(i, min(i + 2, len(extra_channels))):
                channel = extra_channels[j]
                row.append(InlineKeyboardButton("Join", url=channel["link"]))
            keyboard.append(row)
        
        # Add claim button
        keyboard.append([InlineKeyboardButton("🔒claim", callback_data="claim")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"*😍 Hi {username} Welcome To Bot*\n\n*🟢 Must Join All Channels To Use Bot*\n\n◼️ *After Joining Click '🔒claim'*"
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

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
    """Show main menu after delay without showing loading message"""
    try:
        await asyncio.sleep(3)  # Reduced from 8 to 3 seconds

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
            
            # Create webapp URL with user_id parameter
            webapp_url_with_params = f"{WEBAPP_URL}?user_id={user_id}"
            webapp_button = InlineKeyboardButton("✅ Verify Device", web_app=WebAppInfo(url=webapp_url_with_params))
            keyboard = [[webapp_button]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"*✅ Thanks {username}! Now click 'Verify Device' button below to complete device verification.*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        else:
            # Recreate the same join buttons as in start
            keyboard = []
            
            # Add default channels
            keyboard.append([InlineKeyboardButton("Join", url=CHANNEL_LINK),
                            InlineKeyboardButton("Join", url=GROUP_LINK)])
            
            # Add extra channels
            for i in range(0, len(extra_channels), 2):
                row = []
                for j in range(i, min(i + 2, len(extra_channels))):
                    channel = extra_channels[j]
                    row.append(InlineKeyboardButton("Join", url=channel["link"]))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔒claim", callback_data="claim")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = f"*{username}, please join both channel and group first!*\n\n*After joining, click '🔒claim' again.*"

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

# Web app data handler - MODIFIED FOR BETTER ERROR HANDLING
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle web app data when user completes verification"""
    print(f"Web app data received: {update.web_app_data.data}")

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"
    chat_id = update.effective_chat.id

    print(f"Processing verification for user {user_id} ({username}) in chat {chat_id}")

    try:
        # Parse the web app data
        web_data = json.loads(update.web_app_data.data)
        print(f"Parsed web data: {web_data}")
        
        # Check if verification was successful
        if web_data.get('status') == 'success':
            # Mark user as verified and channel member since they reached this point
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
            print(f"User {user_id} marked as verified and saved to data")

            # Send success message
            success_text = f"*✅ DEVICE VERIFICATION SUCCESSFUL!*\n\n*Welcome {username}!*\n\n*Your device has been verified successfully. You can now access all features of the bot.*"
            await context.bot.send_message(chat_id=chat_id, text=success_text, parse_mode="Markdown")

            # Show main menu with delay
            print(f"Starting delayed main menu for user {user_id}")
            await show_delayed_main_menu(chat_id, username, context)
            
        else:
            # Verification failed
            error_msg = web_data.get('message', 'Unknown error')
            error_text = f"*❌ DEVICE VERIFICATION FAILED*\n\n*Reason: {error_msg}*\n\n*Please try again using /start*"
            await context.bot.send_message(chat_id=chat_id, text=error_text, parse_mode="Markdown")
            
    except json.JSONDecodeError:
        print("Failed to parse web app data as JSON")
        # Try to handle as simple string data
        if "success" in update.web_app_data.data.lower():
            # Mark user as verified
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
            
            success_text = f"*✅ DEVICE VERIFICATION SUCCESSFUL!*\n\n*Welcome {username}!*\n\n*Your device has been verified successfully.*"
            await context.bot.send_message(chat_id=chat_id, text=success_text, parse_mode="Markdown")
            await show_delayed_main_menu(chat_id, username, context)
        else:
            error_text = "*❌ Verification error. Please try again using /start*"
            await context.bot.send_message(chat_id=chat_id, text=error_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error processing web app data: {e}")
        error_text = "*❌ Verification error. Please try again using /start*"
        await context.bot.send_message(chat_id=chat_id, text=error_text, parse_mode="Markdown")

# ADD ALL THE REMAINING FUNCTIONS FROM YOUR ORIGINAL BOT.PY HERE
# This includes: handle_message, handle_bonus, handle_withdraw_request, 
# handle_wallet_link, callback_query_handler, and all admin functions

# Placeholder for the rest of your functions - you need to copy them from your original bot.py
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your existing handle_message function
    pass

async def handle_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your existing handle_bonus function
    pass

async def handle_withdraw_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your existing handle_withdraw_request function
    pass

async def handle_wallet_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your existing handle_wallet_link function
    pass

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your existing callback_query_handler function
    pass

# Add all your admin functions here as well...

def main():
    print("Bot is starting...")
    
    # Initialize configuration
    save_config(config)
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Start the bot
    print("Bot started successfully!")
    application.run_polling()

if __name__ == "__main__":
    main()
