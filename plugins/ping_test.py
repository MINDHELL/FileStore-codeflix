from pyrogram import filters
from pyrogram.types import Message
from bot import Bot

@Bot.on_message(filters.command("ping") & filters.private)
async def ping_test(client, message: Message):
    await message.reply_text("🏓 Pong! ✅")

# plugins/subscription.py

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from bot import Bot
from config import *

# Command to show subscription plans
@Bot.on_message(filters.command('plans') & filters.private)
async def show_plans(bot: Bot, message):
    plans_text = PAYMENT_TEXT
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Pay via UPI", callback_data="upi_info")],
        [InlineKeyboardButton("Contact Support", url=f"https://t.me/{OWNER}")]
    ])
    await message.reply(plans_text, reply_markup=buttons, parse_mode=ParseMode.HTML)


# Command to show UPI payment QR code and instructions
@Bot.on_message(filters.command('upi') & filters.private)
async def upi_info(bot: Bot, message):
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=START_PIC,
        caption=PAYMENT_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Contact Owner", url=f"https://t.me/{OWNER}")]]
        )
    )
