from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from bot import Bot
from config import *

# -------------------- /ping command --------------------
@Bot.on_message(filters.command("ping") & filters.private)
async def ping_test(client, message: Message):
    await message.reply_text("🏓 Pong! ✅")


# -------------------- /plans command --------------------
@Bot.on_message(filters.command('plans') & filters.private)
async def show_plans(bot: Bot, message: Message):
    plans_text = PAYMENT_TEXT
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Pay via UPI", callback_data="upi_info")],
        [InlineKeyboardButton("Contact Support", url=f"https://t.me/{OWNER_ID}")]
    ])
    await message.reply(plans_text, reply_markup=buttons, parse_mode=ParseMode.HTML)


# -------------------- /upi command --------------------
@Bot.on_message(filters.command('upi') & filters.private)
async def upi_info(bot: Bot, message: Message):
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=START_PIC,  # Replace with PAYMENT_QR if you have a QR image
        caption=PAYMENT_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Contact Owner", url=f"https://t.me/{OWNER_ID}")]]
        )
    )


# -------------------- Callback for "Pay via UPI" button --------------------
@Bot.on_callback_query(filters.regex("upi_info"))
async def upi_button_handler(bot: Bot, query: CallbackQuery):
    # Stop the loading animation
    await query.answer()

    # Send the payment QR code
    await bot.send_photo(
        chat_id=query.from_user.id,
        photo=START_PIC,  # Replace with PAYMENT_QR if you have a QR image
        caption=PAYMENT_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Contact Owner", url=f"https://t.me/{OWNER_ID}")]]
        )
    )
