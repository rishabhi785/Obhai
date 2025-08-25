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
BACKEND_URL = "https://9d4f4c9d-ffeb-441c-8677-be836689e54d-00-2c2givkv2clmi.pike.replit.dev/verify"
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

# Backend verification function
async def verify_device_with_backend(user_id, web_app_data):
    """Send device data to backend for verification"""
    try:
        # Parse web app data
        device_data = json.loads(web_app_data)
        
        # Prepare payload for backend
        payload = {
            'user_id': user_id,
            'device_data': device_data
        }
        
        # Send to backend
        async with aiohttp.ClientSession() as session:
            async with session.post(BACKEND_URL, json=payload) as response:
                return await response.json()
                
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

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
            
            # Create webapp URL with user_id parameter
            webapp_url = f"{WEBAPP_URL}?user_id={user_id}"
            webapp_button = InlineKeyboardButton("✅ Verify", web_app=WebAppInfo(url=webapp_url))
            keyboard = [[webapp_button]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"*✅ Thanks {username}! Now click 'Verify' button below to complete device verification.*",
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

# Web app data handler with backend integration
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle web app data when user completes verification"""
    print(f"Web app data received: {update.web_app_data.data}")

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"
    chat_id = update.effective_chat.id

    print(f"Processing verification for user {user_id} ({username}) in chat {chat_id}")

    try:
        # Send device data to backend for verification
        verification_result = await verify_device_with_backend(user_id, update.web_app_data.data)
        
        if verification_result.get('status') == 'success':
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
            print(f"User {user_id} marked as verified and saved to data")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*✅ Device Verification Successful!*\n\n*Welcome {username}!* You can now access all features.",
                parse_mode="Markdown"
            )
            
            # Show main menu with delay
            print(f"Starting delayed main menu for user {user_id}")
            await show_delayed_main_menu(chat_id, username, context)
            
        else:
            # Verification failed
            error_msg = verification_result.get('message', 'Verification failed')
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*❌ Verification Failed*\n\n*Reason:* {error_msg}\n\nPlease try again using /start",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        print(f"Error in web app data handler: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="*❌ Verification error. Please try again using /start*",
            parse_mode="Markdown"
        )

# Admin Panel Functions for Channel Management
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with channel management options"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied. Admin only.*", parse_mode="Markdown")
        return
    
    keyboard = [
        ["📋 View Channels", "➕ Add Channel"],
        ["🗑️ Remove Channel", "👥 User Stats"],
        ["📢 Broadcast", "📣 Channel Post"],
        ["⚙️ Bot Settings", "🔙 Main Menu"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = "*🔧 ADMIN PANEL*\n\n*Channel Management:*\n• View all required channels\n• Add new channels with verification\n• Remove channels from list\n\n*Other Options:*\n• View user statistics\n• Manage bot settings"
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def view_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all current channels"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied.*", parse_mode="Markdown")
        return
    
    # Show default channels + extra channels
    text = "*📋 REQUIRED CHANNELS*\n\n*Default Channels:*\n"
    text += f"1. {CHANNEL_LINK}\n"
    text += f"2. {GROUP_LINK}\n\n"
    
    if extra_channels:
        text += f"*Additional Channels ({len(extra_channels)}):*\n"
        for i, channel in enumerate(extra_channels, 3):
            text += f"{i}. {channel['name']}\n"
            text += f"   🔗 {channel['link']}\n"
            text += f"   🆔 {channel['id']}\n"
            text += f"   📱 Type: {channel['type']}\n\n"
    else:
        text += "*No additional channels configured.*"
    
    keyboard = [
        ["➕ Add Channel", "🗑️ Remove Channel"],
        ["🔙 Admin Panel"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def add_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to add a new channel"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied.*", parse_mode="Markdown")
        return
    
    user_states[user_id] = WAITING_FOR_CHANNEL
    
    text = "*➕ ADD NEW CHANNEL*\n\n*Please send the channel link or username:*\n\n*Examples:*\n• `https://t.me/yourchannel`\n• `@yourchannel`\n\n*Note: The bot must be added as admin to the channel for verification.*"
    
    keyboard = [["🔙 Admin Panel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def remove_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to remove a channel"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied.*", parse_mode="Markdown")
        return
    
    if not extra_channels:
        await update.message.reply_text("*❌ No additional channels to remove.*", parse_mode="Markdown")
        return
    
    user_states[user_id] = WAITING_FOR_CHANNEL_REMOVE
    keyboard = []
    for channel in extra_channels:
        keyboard.append([f"🗑️ Remove: {channel['name']}"])
    
    keyboard.append(["🔙 Admin Panel"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = "*🗑️ REMOVE CHANNEL*\n\n*Select a channel to remove:*"
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def process_channel_addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new channel addition"""
    user_id = str(update.effective_user.id)
    global extra_channels
    
    if user_id != ADMIN_ID or user_states.get(user_id) != WAITING_FOR_CHANNEL:
        return
    
    channel_link = update.message.text.strip()
    
    # Show processing message
    processing_msg = await update.message.reply_text("*🔄 Validating channel...*", parse_mode="Markdown")
    
    try:
        # Validate the channel
        validation_result = await validate_channel(context, channel_link)
        
        if not validation_result["valid"]:
            await processing_msg.edit_text(f"*❌ Channel validation failed:*\n\n{validation_result['error']}", parse_mode="Markdown")
            return
        
        # Check if channel already exists (including default ones)
        if validation_result["chat_id"] in [CHANNEL_ID, GROUP_ID]:
            await processing_msg.edit_text("*❌ This is already a default channel.*", parse_mode="Markdown")
            return
            
        for existing_channel in extra_channels:
            if existing_channel["id"] == validation_result["chat_id"]:
                await processing_msg.edit_text("*❌ This channel is already in the list.*", parse_mode="Markdown")
                return
        
        # Add the new channel
        new_channel = {
            "id": validation_result["chat_id"],
            "link": channel_link,
            "name": validation_result["title"],
            "type": validation_result["type"]
        }
        
        extra_channels.append(new_channel)
        save_extra_channels(extra_channels)
        
        # Clear user state
        if user_id in user_states:
            del user_states[user_id]
        
        # Show success message
        text = f"*✅ Channel Added Successfully!*\n\n*Name:* {validation_result['title']}\n*Type:* {validation_result['type']}\n*ID:* {validation_result['chat_id']}\n*Link:* {channel_link}"
        
        keyboard = [
            ["📋 View Channels", "➕ Add Another"],
            ["🔙 Admin Panel"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await processing_msg.edit_text(text, parse_mode="Markdown")
        await update.message.reply_text("*Choose your next action:*", reply_markup=reply_markup, parse_mode="Markdown")
        
    except Exception as e:
        await processing_msg.edit_text(f"*❌ Error adding channel:*\n\n{str(e)}", parse_mode="Markdown")

async def process_channel_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process channel removal"""
    user_id = str(update.effective_user.id)
    global extra_channels
    
    if user_id != ADMIN_ID or user_states.get(user_id) != WAITING_FOR_CHANNEL_REMOVE:
        return
    
    text = update.message.text
    
    if text == "🔙 Admin Panel":
        if user_id in user_states:
            del user_states[user_id]
        await show_admin_panel(update, context)
        return
    
    if not text.startswith("🗑️ Remove: "):
        return
    
    channel_name = text.replace("🗑️ Remove: ", "")
    
    # Find and remove the channel
    removed_channel = None
    new_extra_channels = []
    
    for channel in extra_channels:
        if channel["name"] == channel_name:
            removed_channel = channel
        else:
            new_extra_channels.append(channel)
    
    if removed_channel:
        extra_channels = new_extra_channels
        save_extra_channels(extra_channels)
        
        # Clear user state
        if user_id in user_states:
            del user_states[user_id]
        
        text = f"*✅ Channel Removed Successfully!*\n\n*Removed:* {removed_channel['name']}\n*Link:* {removed_channel['link']}"
    else:
        text = "*❌ Channel not found.*"
    
    keyboard = [
        ["📋 View Channels", "🗑️ Remove Another"],
        ["🔙 Admin Panel"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied.*", parse_mode="Markdown")
        return
    
    total_users = len(users_data)
    verified_users = sum(1 for user in users_data.values() if user.get("verified", False))
    total_balance = sum(user.get("balance", 0) for user in users_data.values())
    total_referrals = sum(user.get("referrals", 0) for user in users_data.values())
    
    text = f"*👥 USER STATISTICS*\n\n"
    text += f"*Total Users:* {total_users}\n"
    text += f"*Verified Users:* {verified_users}\n"
    text += f"*Total Balance:* ₹{total_balance}\n"
    text += f"*Total Referrals:* {total_referrals}\n"
    text += f"*Required Channels:* {2 + len(extra_channels)} (2 default + {len(extra_channels)} additional)"
    
    keyboard = [["🔙 Admin Panel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_bot_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot settings and configuration"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied.*", parse_mode="Markdown")
        return
    
    text = f"*⚙️ BOT SETTINGS*\n\n"
    text += f"*💰 Minimum Withdrawal:* ₹{config['min_withdrawal']}\n"
    text += f"*🎁 Daily Bonus Amount:* ₹{config['daily_bonus']}\n"
    text += f"*🎯 Referral Bonus:* ₹{config['referral_bonus']}\n\n"
    text += f"*📊 Configuration:*\n"
    text += f"• VSV API Status: Connected\n"
    text += f"• Total Channels: {2 + len(extra_channels)}\n"
    text += f"• Bot Status: Running\n\n"
    text += f"*💡 Quick Settings:*\n"
    text += f"• Type 'SET MIN X' to change minimum withdrawal\n"
    text += f"• Type 'SET BONUS X' to change daily bonus\n"
    text += f"• Type 'SET REFERRAL X' to change referral bonus"
    
    keyboard = [["🔙 Admin Panel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast message process"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied.*", parse_mode="Markdown")
        return
    
    user_states[user_id] = WAITING_FOR_BROADCAST
    
    total_users = len([uid for uid in users_data if users_data[uid].get("verified", False)])
    
    text = f"*📢 BROADCAST MESSAGE*\n\n*Ready to send message to {total_users} verified users*\n\n*Please type your broadcast message:*\n\n*Note: Message will be sent to all users who have started and verified the bot.*"
    
    keyboard = [["🔙 Admin Panel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def start_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start channel post process"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("*❌ Access denied.*", parse_mode="Markdown")
        return
    
    # First check which channels bot is admin in
    admin_channels = await get_admin_channels(context)
    
    if not admin_channels:
        text = "*❌ Bot is not admin in any channels.*\n\n*Make sure to add bot as admin in channels where you want to post.*"
        keyboard = [["🔙 Admin Panel"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return
    
    user_states[user_id] = WAITING_FOR_CHANNEL_POST
    
    # Store admin channels in context for later use
    if not hasattr(context, 'user_data') or context.user_data is None:
        context.user_data = {}
    context.user_data['admin_channels'] = admin_channels
    
    channel_list = "\n".join([f"• {ch['name']}" for ch in admin_channels])
    
    text = f"*📣 CHANNEL POST*\n\n*Bot is admin in {len(admin_channels)} channels:*\n\n{channel_list}\n\n*Please type your message to post in all these channels:*"
    
    keyboard = [["🔙 Admin Panel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def get_admin_channels(context):
    """Get all channels where bot is admin"""
    admin_channels = []
    
    # Check default channels
    try:
        channel = await context.bot.get_chat(CHANNEL_ID)
        member = await context.bot.get_chat_member(CHANNEL_ID, context.bot.id)
        if member.status in ['administrator', 'creator']:
            admin_channels.append({
                "id": CHANNEL_ID,
                "name": channel.title,
                "type": channel.type
            })
    except Exception:
        pass
    
    try:
        group = await context.bot.get_chat(GROUP_ID)
        member = await context.bot.get_chat_member(GROUP_ID, context.bot.id)
        if member.status in ['administrator', 'creator']:
            admin_channels.append({
                "id": GROUP_ID,
                "name": group.title,
                "type": group.type
            })
    except Exception:
        pass
    
    # Check extra channels
    for channel in extra_channels:
        try:
            chat = await context.bot.get_chat(channel["id"])
            member = await context.bot.get_chat_member(channel["id"], context.bot.id)
            if member.status in ['administrator', 'creator']:
                admin_channels.append({
                    "id": channel["id"],
                    "name": chat.title,
                    "type": chat.type
                })
        except Exception:
            continue
    
    return admin_channels

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process broadcast message"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID or user_states.get(user_id) != WAITING_FOR_BROADCAST:
        return
    
    message_text = update.message.text
    total_users = len([uid for uid in users_data if users_data[uid].get("verified", False)])
    
    # Show processing message
    processing_msg = await update.message.reply_text(f"*📤 Sending broadcast to {total_users} users...*", parse_mode="Markdown")
    
    success_count = 0
    failed_count = 0
    
    # Send to all verified users
    for uid, user_data in users_data.items():
        if user_data.get("verified", False):
            try:
                await context.bot.send_message(uid, message_text)
                success_count += 1
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Failed to send to {uid}: {e}")
                failed_count += 1
    
    # Clear user state
    if user_id in user_states:
        del user_states[user_id]
    
    # Show results
    text = f"*✅ Broadcast Complete!*\n\n*Sent to:* {success_count} users\n*Failed:* {failed_count} users\n*Total:* {total_users} users"
    
    keyboard = [["🔙 Admin Panel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await processing_msg.edit_text(text, parse_mode="Markdown")
    await update.message.reply_text("*Choose your next action:*", reply_markup=reply_markup, parse_mode="Markdown")

async def process_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process channel post"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID or user_states.get(user_id) != WAITING_FOR_CHANNEL_POST:
        return
    
    message_text = update.message.text
    admin_channels = context.user_data.get('admin_channels', [])
    
    # Show processing message
    processing_msg = await update.message.reply_text(f"*📤 Posting to {len(admin_channels)} channels...*", parse_mode="Markdown")
    
    success_count = 0
    failed_count = 0
    
    # Post to all admin channels
    for channel in admin_channels:
        try:
            await context.bot.send_message(channel["id"], message_text)
            success_count += 1
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Failed to post to {channel['name']}: {e}")
            failed_count += 1
    
    # Clear user state
    if user_id in user_states:
        del user_states[user_id]
    
    # Show results
    text = f"*✅ Channel Post Complete!*\n\n*Posted to:* {success_count} channels\n*Failed:* {failed_count} channels\n*Total:* {len(admin_channels)} channels"
    
    keyboard = [["🔙 Admin Panel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await processing_msg.edit_text(text, parse_mode="Markdown")
    await update.message.reply_text("*Choose your next action:*", reply_markup=reply_markup, parse_mode="Markdown")

async def process_settings_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process bot settings changes"""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        return
    
    text = update.message.text.upper()
    
    if text.startswith("SET MIN "):
        try:
            amount = float(text.replace("SET MIN ", "").strip())
            if amount < 1:
                await update.message.reply_text("*❌ Minimum withdrawal must be at least ₹1*", parse_mode="Markdown")
                return
            
            config["min_withdrawal"] = amount
            save_config(config)
            await update.message.reply_text(f"*✅ Minimum withdrawal set to ₹{amount}*", parse_mode="Markdown")
            
        except ValueError:
            await update.message.reply_text("*❌ Invalid amount format*", parse_mode="Markdown")
    
    elif text.startswith("SET BONUS "):
        try:
            amount = float(text.replace("SET BONUS ", "").strip())
            if amount < 0:
                await update.message.reply_text("*❌ Bonus amount cannot be negative*", parse_mode="Markdown")
                return
            
            config["daily_bonus"] = amount
            save_config(config)
            await update.message.reply_text(f"*✅ Daily bonus set to ₹{amount}*", parse_mode="Markdown")
            
        except ValueError:
            await update.message.reply_text("*❌ Invalid amount format*", parse_mode="Markdown")
    
    elif text.startswith("SET REFERRAL "):
        try:
            amount = float(text.replace("SET REFERRAL ", "").strip())
            if amount < 0:
                await update.message.reply_text("*❌ Referral bonus cannot be negative*", parse_mode="Markdown")
                return
            
            config["referral_bonus"] = amount
            save_config(config)
            await update.message.reply_text(f"*✅ Referral bonus set to ₹{amount}*", parse_mode="Markdown")
            
        except ValueError:
            await update.message.reply_text("*❌ Invalid amount format*", parse_mode="Markdown")

# Balance, Referral, Bonus, Withdraw, and Wallet functions
async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance request"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data:
        await start(update, context)
        return
    
    balance = users_data[user_id].get("balance", 0)
    referrals = users_data[user_id].get("referrals", 0)
    
    text = f"*💰 YOUR BALANCE*\n\n*Current Balance:* ₹{balance}\n*Total Referrals:* {referrals}\n*Referral Bonus:* ₹{config['referral_bonus']} per user\n\n*💡 Tip:* Invite friends to earn more!"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle referral request"""
    user_id = str(update.effective_user.id)
    bot_username = context.bot.username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    text = f"*📤 YOUR REFERRAL LINK*\n\n*Share this link with friends:*\n`{referral_link}`\n\n*💰 You earn ₹{config['referral_bonus']} for each friend who joins and verifies!*"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bonus claim"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data:
        await start(update, context)
        return
    
    now = datetime.now()
    last_bonus = users_data[user_id].get("last_bonus")
    
    # Check if bonus already claimed today
    if last_bonus:
        last_date = datetime.fromisoformat(last_bonus)
        if last_date.date() == now.date():
            # Calculate time until next bonus
            next_date = last_date + timedelta(days=1)
            time_left = next_date - now
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            text = f"*⏰ BONUS ALREADY CLAIMED*\n\n*You already claimed your daily bonus today.*\n*Next bonus available in:* {hours_left}h {minutes_left}m"
            await update.message.reply_text(text, parse_mode="Markdown")
            return
    
    # Give bonus
    bonus_amount = config["daily_bonus"]
    users_data[user_id]["balance"] += bonus_amount
    users_data[user_id]["last_bonus"] = now.isoformat()
    save_users_data(users_data)
    
    text = f"*🎁 DAILY BONUS CLAIMED*\n\n*You received:* ₹{bonus_amount}\n*New balance:* ₹{users_data[user_id]['balance']}\n\n*Come back tomorrow for another bonus!*"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal request"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data:
        await start(update, context)
        return
    
    balance = users_data[user_id].get("balance", 0)
    wallet_number = users_data[user_id].get("wallet_number")
    
    if not wallet_number:
        text = f"*❌ WALLET NOT LINKED*\n\n*Please link your VSV wallet first to withdraw funds.*\n*Minimum withdrawal:* ₹{config['min_withdrawal']}"
        await update.message.reply_text(text, parse_mode="Markdown")
        return
    
    if balance < config["min_withdrawal"]:
        text = f"*❌ INSUFFICIENT BALANCE*\n\n*Your balance:* ₹{balance}\n*Minimum withdrawal:* ₹{config['min_withdrawal']}\n*You need:* ₹{config['min_withdrawal'] - balance} more"
        await update.message.reply_text(text, parse_mode="Markdown")
        return
    
    # Ask for withdrawal amount
    text = f"*💸 WITHDRAW FUNDS*\n\n*Your balance:* ₹{balance}\n*Linked wallet:* {wallet_number}\n*Minimum withdrawal:* ₹{config['min_withdrawal']}\n\n*Please enter the amount you want to withdraw:*"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process withdrawal amount"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data:
        return
    
    try:
        amount = float(update.message.text)
        balance = users_data[user_id].get("balance", 0)
        wallet_number = users_data[user_id].get("wallet_number")
        
        if amount < config["min_withdrawal"]:
            await update.message.reply_text(f"*❌ Amount below minimum withdrawal of ₹{config['min_withdrawal']}*", parse_mode="Markdown")
            return
        
        if amount > balance:
            await update.message.reply_text(f"*❌ Insufficient balance. You have ₹{balance}*", parse_mode="Markdown")
            return
        
        # Process withdrawal
        processing_msg = await update.message.reply_text("*🔄 Processing withdrawal...*", parse_mode="Markdown")
        
        result = await transfer_money_via_vsv(wallet_number, amount, user_id)
        
        if result["success"]:
            # Deduct from balance
            users_data[user_id]["balance"] -= amount
            save_users_data(users_data)
            
            text = f"*✅ WITHDRAWAL SUCCESSFUL!*\n\n*Amount:* ₹{amount}\n*Sent to:* {wallet_number}\n*Transaction ID:* {result['transaction_id']}\n*New balance:* ₹{users_data[user_id]['balance']}"
            
            await processing_msg.edit_text(text, parse_mode="Markdown")
            
            # Notify admin
            try:
                admin_text = f"*💰 WITHDRAWAL NOTIFICATION*\n\n*User:* {update.effective_user.first_name} (@{update.effective_user.username or 'N/A'})\n*User ID:* {user_id}\n*Amount:* ₹{amount}\n*Wallet:* {wallet_number}\n*Transaction ID:* {result['transaction_id']}"
                await context.bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to notify admin: {e}")
                
        else:
            text = f"*❌ WITHDRAWAL FAILED*\n\n*Error:* {result['error']}\n\n*Please try again later or contact support.*"
            await processing_msg.edit_text(text, parse_mode="Markdown")
            
    except ValueError:
        await update.message.reply_text("*❌ Please enter a valid amount*", parse_mode="Markdown")

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle wallet linking"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data:
        await start(update, context)
        return
    
    wallet_number = users_data[user_id].get("wallet_number")
    
    if wallet_number:
        text = f"*🏦 YOUR WALLET*\n\n*Linked VSV Wallet:* {wallet_number}\n\n*To change your wallet, send your new 10-digit VSV wallet number:*"
    else:
        text = f"*🏦 LINK VSV WALLET*\n\n*To withdraw funds, you need to link your VSV wallet.*\n\n*Please send your 10-digit VSV wallet number:*"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def process_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process wallet number"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data:
        return
    
    wallet_number = update.message.text.strip()
    
    if not validate_wallet_number(wallet_number):
        await update.message.reply_text("*❌ Invalid VSV wallet number. Please enter a valid 10-digit number.*", parse_mode="Markdown")
        return
    
    users_data[user_id]["wallet_number"] = wallet_number
    save_users_data(users_data)
    
    text = f"*✅ WALLET LINKED SUCCESSFULLY!*\n\n*VSV Wallet:* {wallet_number}\n\n*You can now withdraw your earnings to this wallet.*"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# Main message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    if update.effective_chat.type != "private":
        return

    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    # Check if user is in the middle of an admin process
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == WAITING_FOR_CHANNEL:
            await process_channel_addition(update, context)
            return
        elif state == WAITING_FOR_CHANNEL_REMOVE:
            await process_channel_removal(update, context)
            return
        elif state == WAITING_FOR_BROADCAST:
            await process_broadcast(update, context)
            return
        elif state == WAITING_FOR_CHANNEL_POST:
            await process_channel_post(update, context)
            return
    
    # Check if user is verified
    if not users_data.get(user_id, {}).get("verified", False):
        await update.message.reply_text("*❌ Please complete verification first using /start*", parse_mode="Markdown")
        return
    
    # Handle admin panel commands
    if message_text == "🔧 ADMIN PANEL" and user_id == ADMIN_ID:
        await show_admin_panel(update, context)
        return
    elif message_text == "📋 View Channels" and user_id == ADMIN_ID:
        await view_channels(update, context)
        return
    elif message_text == "➕ Add Channel" and user_id == ADMIN_ID:
        await add_channel_prompt(update, context)
        return
    elif message_text == "🗑️ Remove Channel" and user_id == ADMIN_ID:
        await remove_channel_prompt(update, context)
        return
    elif message_text == "👥 User Stats" and user_id == ADMIN_ID:
        await show_user_stats(update, context)
        return
    elif message_text == "📢 Broadcast" and user_id == ADMIN_ID:
        await start_broadcast(update, context)
        return
    elif message_text == "📣 Channel Post" and user_id == ADMIN_ID:
        await start_channel_post(update, context)
        return
    elif message_text == "⚙️ Bot Settings" and user_id == ADMIN_ID:
        await show_bot_settings(update, context)
        return
    elif message_text == "🔙 Admin Panel" and user_id == ADMIN_ID:
        await show_admin_panel(update, context)
        return
    elif message_text == "🔙 Main Menu":
        await show_main_menu(update, context)
        return
    
    # Handle admin settings changes
    if user_id == ADMIN_ID and (
        message_text.startswith("SET MIN ") or 
        message_text.startswith("SET BONUS ") or 
        message_text.startswith("SET REFERRAL ")
    ):
        await process_settings_change(update, context)
        return
    
    # Handle user commands
    if message_text == "BALANCE":
        await handle_balance(update, context)
    elif message_text == "REFERAL LINK":
        await handle_referral(update, context)
    elif message_text == "BONUS":
        await handle_bonus(update, context)
    elif message_text == "WITHDRAW":
        await handle_withdraw(update, context)
    elif message_text == "LINK WALLET":
        await handle_wallet(update, context)
    elif re.match(r'^\d+(\.\d+)?$', message_text) and users_data.get(user_id, {}).get("wallet_number"):
        # If user has wallet linked and sends a number, assume it's a withdrawal amount
        await process_withdrawal(update, context)
    elif re.match(r'^\d{10}$', message_text):
        # If user sends a 10-digit number, assume it's a wallet number
        await process_wallet(update, context)
    else:
        await update.message.reply_text("*❌ Unknown command. Use the menu buttons.*", parse_mode="Markdown")

# Callback query handler
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    if query.data == "claim":
        await claim_callback(update, context)
    else:
        await query.answer("Unknown button")

def main():
    print("🤖 Bot is starting...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    print("✅ Bot started successfully!")
    application.run_polling()

if __name__ == "__main__":
    main()
