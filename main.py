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
BACKEND_URL = "https://9d4f4c9d-ffeb-441c-8677-be836689e54d-00-2c2givkv2clmi.pike.replit.dev"
ADMIN_ID = "6736711885"

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

# Global variables
user_states = {}
users_data = {}
redeem_codes = []
config = DEFAULT_CONFIG.copy()
extra_channels = []

# Load configuration
def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Load additional channels
def load_extra_channels():
    global extra_channels
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r') as f:
            data = json.load(f)
            extra_channels = data.get('extra_channels', [])
    return extra_channels

def save_extra_channels(channels):
    data = {'extra_channels': channels}
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Load data functions
def load_users_data():
    global users_data
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            users_data = json.load(f)
    return users_data

def save_users_data(data):
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_redeem_codes():
    global redeem_codes
    if os.path.exists(REDEEM_CODES_FILE):
        with open(REDEEM_CODES_FILE, 'r') as f:
            redeem_codes = json.load(f)
    return redeem_codes

def save_redeem_codes(codes):
    with open(REDEEM_CODES_FILE, 'w') as f:
        json.dump(codes, f, indent=2)

# Initialize data
load_config()
load_extra_channels()
load_users_data()
load_redeem_codes()

async def check_membership(context, user_id):
    """Simplified membership check - only check default channels"""
    try:
        # Check only default channels for faster response
        try:
            channel_member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
            group_member = await context.bot.get_chat_member(GROUP_ID, user_id)
            
            if (channel_member.status in ['member', 'administrator', 'creator'] and 
                group_member.status in ['member', 'administrator', 'creator']):
                return True
            return False
        except Exception as e:
            print(f"Error checking membership for user {user_id}: {e}")
            return False
            
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

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

    # Check if user is already verified
    if users_data[user_id].get("verified", False):
        await show_main_menu(update, context)
        return

    # Create join buttons
    keyboard = []
    keyboard.append([InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)])
    keyboard.append([InlineKeyboardButton("👥 Join Group", url=GROUP_LINK)])
    keyboard.append([InlineKeyboardButton("✅ I Have Joined", callback_data="claim")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""*👋 Welcome {username}!*

*📋 To use this bot, please:*
1. Join our channel: {CHANNEL_LINK}
2. Join our group: {GROUP_LINK}

*After joining, click ✅ I Have Joined*"""

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu to user"""
    try:
        user_id = str(update.effective_user.id)
        username = update.effective_user.first_name or "User"
        
        if user_id == ADMIN_ID:
            keyboard = [
                ["💰 BALANCE", "📤 REFERAL LINK"],
                ["🎁 BONUS", "💸 WITHDRAW"],
                ["🏦 LINK WALLET", "🔧 ADMIN PANEL"]
            ]
        else:
            keyboard = [
                ["💰 BALANCE", "📤 REFERAL LINK"],
                ["🎁 BONUS", "💸 WITHDRAW"],
                ["🏦 LINK WALLET"]
            ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        menu_text = f"""*🏠 MAIN MENU*

*Welcome {username}!*

Choose an option below:"""

        if hasattr(update, 'message'):
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=menu_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

    except Exception as e:
        print(f"Error showing main menu: {e}")

async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    username = query.from_user.first_name or "User"

    try:
        await query.answer("🔍 Checking membership...")
    except Exception as e:
        print(f"Error answering callback: {e}")

    # Show loading message
    await query.edit_message_text("*🔍 Checking if you joined channels...*", parse_mode="Markdown")

    try:
        # Check membership with timeout
        is_member = await asyncio.wait_for(check_membership(context, user_id), timeout=10.0)
        
        if is_member:
            users_data[user_id]["joined_channels"] = True
            save_users_data(users_data)
            
            # Create webapp URL with user_id parameter
            webapp_url_with_params = f"{WEBAPP_URL}?user_id={user_id}"
            webapp_button = InlineKeyboardButton("📱 Verify Device", web_app=WebAppInfo(url=webapp_url_with_params))
            keyboard = [[webapp_button]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"""*✅ Membership Verified!*

*Welcome {username}!* 

Now please click *📱 Verify Device* to complete device verification.""",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        else:
            # Recreate join buttons
            keyboard = []
            keyboard.append([InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)])
            keyboard.append([InlineKeyboardButton("👥 Join Group", url=GROUP_LINK)])
            keyboard.append([InlineKeyboardButton("✅ I Have Joined", callback_data="claim")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"""*❌ Not Joined Yet*

*{username},* it seems you haven't joined our channels yet.

Please join both and try again.""",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
    except asyncio.TimeoutError:
        await query.edit_message_text(
            "*⏰ Timeout! Please try again in a moment.*",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error in claim callback: {e}")
        await query.edit_message_text(
            "*❌ Error checking membership. Please try again.*",
            parse_mode="Markdown"
        )

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle web app verification result - SIMPLIFIED VERSION"""
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"
    chat_id = update.effective_chat.id

    print(f"Web app data received from user {user_id}")
    print(f"Raw data: {update.web_app_data.data}")

    try:
        # Mark user as verified regardless of web app data
        # Backend will handle the actual verification and send messages
        users_data[user_id]["verified"] = True
        save_users_data(users_data)
        
        # Just show a waiting message - backend will send the actual result
        await context.bot.send_message(
            chat_id=chat_id,
            text="*🔄 Verification in progress... Backend is processing your device verification.*",
            parse_mode="Markdown"
        )
        
        # Show main menu after a short delay
        await asyncio.sleep(2)
        await show_main_menu(update, context)
        
    except Exception as e:
        print(f"Error in web app handler: {e}")
        error_text = "*❌ Verification error. Please try again using /start*"
        await context.bot.send_message(chat_id=chat_id, text=error_text, parse_mode="Markdown")

# Basic message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_id = str(update.effective_user.id)
    message_text = update.message.text

    # Check if user is verified
    if not users_data.get(user_id, {}).get("verified", False):
        await update.message.reply_text("*❌ Please complete verification first using /start*", parse_mode="Markdown")
        return

    # Handle basic commands
    if message_text == "💰 BALANCE":
        balance = users_data[user_id].get("balance", 0)
        await update.message.reply_text(f"*💰 Your Balance: ₹{balance}*", parse_mode="Markdown")

    elif message_text == "📤 REFERAL LINK":
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        await update.message.reply_text(f"*📤 Your Referral Link:*\n`{referral_link}`", parse_mode="Markdown")

    elif message_text == "🎁 BONUS":
        await update.message.reply_text("*🎁 Bonus feature coming soon!*", parse_mode="Markdown")

    elif message_text == "💸 WITHDRAW":
        await update.message.reply_text("*💸 Withdrawal feature coming soon!*", parse_mode="Markdown")

    elif message_text == "🏦 LINK WALLET":
        await update.message.reply_text("*🏦 Wallet linking feature coming soon!*", parse_mode="Markdown")

    elif message_text == "🔧 ADMIN PANEL" and user_id == ADMIN_ID:
        await update.message.reply_text("*🔧 Admin panel coming soon!*", parse_mode="Markdown")

    elif message_text == "/start":
        await start(update, context)

    else:
        await update.message.reply_text("*❌ Unknown command. Use the menu buttons.*", parse_mode="Markdown")

def main():
    print("🤖 Bot is starting...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    application.add_handler(CallbackQueryHandler(claim_callback))
    
    print("✅ Bot started successfully!")
    application.run_polling()

if __name__ == "__main__":
    main()
