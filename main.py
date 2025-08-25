import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Zeabur environment variables se config
BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "https://9d4f4c9d-ffeb-441c-8677-be836689e54d-00-2c2givkv2clmi.pike.replit.dev")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://row-vert.vercel.app")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    frontend_with_params = f"{FRONTEND_URL}?user_id={user_id}"
    
    keyboard = [[InlineKeyboardButton("Verify Device", url=frontend_with_params)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome! Please verify your device to continue:\n\n"
        "Click the button below to start device verification:",
        reply_markup=reply_markup
    )

async def check_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # You can implement a call to your backend to check verification status
    # For now, just prompt the user to verify
    frontend_with_params = f"{FRONTEND_URL}?user_id={user_id}"
    keyboard = [[InlineKeyboardButton("Verify Device", url=frontend_with_params)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Check your verification status or verify your device:",
        reply_markup=reply_markup
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verify", check_verification))
    application.run_polling()

if __name__ == '__main__':
    main()
