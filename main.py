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
WEBAPP_URL = "https://row-vert.vercel.app"
ADMIN_ID = "6736711885"

# Data files
USERS_FILE = "users_data.json"

# Load data functions
def load_users_data():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users_data(data):
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Global data
users_data = load_users_data()

async def check_membership(context, user_id):
    """Check if user joined required channels"""
    try:
        channel_member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        group_member = await context.bot.get_chat_member(GROUP_ID, user_id)
        
        return (channel_member.status in ['member', 'administrator', 'creator'] and 
                group_member.status in ['member', 'administrator', 'creator'])
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    if update.effective_chat.type != "private":
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"

    # Initialize user data
    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 5.00,
            "verified": False
        }
        save_users_data(users_data)

    # Check if already verified
    if users_data[user_id].get("verified", False):
        await show_main_menu(update, context)
        return

    # Show join channels message
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👥 Join Group", url=GROUP_LINK)],
        [InlineKeyboardButton("✅ I Have Joined", callback_data="claim")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""*👋 Welcome {username}!*

*📋 To use this bot, please:*
1. Join our channel: {CHANNEL_LINK}
2. Join our group: {GROUP_LINK}

*After joining, click ✅ I Have Joined*"""

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle claim button click"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    username = query.from_user.first_name or "User"

    await query.answer("🔍 Checking membership...")

    try:
        # Check membership
        is_member = await check_membership(context, user_id)
        
        if is_member:
            users_data[user_id]["verified"] = True
            save_users_data(users_data)
            
            # Show verify button
            webapp_url = f"{WEBAPP_URL}?user_id={user_id}"
            keyboard = [[InlineKeyboardButton("📱 Verify Device", web_app=WebAppInfo(url=webapp_url))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"""*✅ Membership Verified!*

*Welcome {username}!* 

Now please click *📱 Verify Device* to complete device verification.""",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            # Show join buttons again
            keyboard = [
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("👥 Join Group", url=GROUP_LINK)],
                [InlineKeyboardButton("✅ I Have Joined", callback_data="claim")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"*❌ Not Joined Yet*\n\n*{username},* please join both channels first!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await query.edit_message_text("*❌ Error checking membership. Please try again.*", parse_mode="Markdown")

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle web app verification result"""
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name or "User"

    # Mark as verified and show main menu
    users_data[user_id]["verified"] = True
    save_users_data(users_data)
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"*✅ Device Verification Successful!*\n\n*Welcome {username}!* You can now access all features.",
        parse_mode="Markdown"
    )
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu to verified users"""
    user_id = str(update.effective_user.id)
    
    keyboard = [
        ["💰 BALANCE", "💸 WITHDRAW"]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if hasattr(update, 'message'):
        await update.message.reply_text("*🏠 MAIN MENU*\n\nUse the buttons below:", reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="*🏠 MAIN MENU*\n\nUse the buttons below:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    if update.effective_chat.type != "private":
        return

    user_id = str(update.effective_user.id)
    message_text = update.message.text

    # Check if user is verified
    if user_id not in users_data or not users_data[user_id].get("verified", False):
        await update.message.reply_text("*❌ Please complete verification first using /start*", parse_mode="Markdown")
        return

    # Handle user commands
    if message_text == "💰 BALANCE":
        balance = users_data[user_id].get("balance", 0)
        await update.message.reply_text(f"*💰 Balance: ₹{balance:.2f}*\n\n*Use 'Withdraw' button to withdraw your balance to UPI*", parse_mode="Markdown")
    
    elif message_text == "💸 WITHDRAW":
        await update.message.reply_text("*⏳ Withdrawal feature coming soon!*", parse_mode="Markdown")
    
    elif message_text == "/start":
        await start(update, context)
    
    else:
        await update.message.reply_text("*❌ Unknown command. Use the menu buttons.*", parse_mode="Markdown")

# Callback query handler
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "claim":
        await claim_callback(update, context)

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
