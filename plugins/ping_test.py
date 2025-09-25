from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from bot import Bot
from config import *
from database.db_premium import check_user_plan, is_premium_user
import time

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
        [InlineKeyboardButton("Contact Support", url=f"https://t.me/{OWNER}")]
    ])
    await message.reply(plans_text, reply_markup=buttons, parse_mode=ParseMode.HTML)


# -------------------- /upi command --------------------
@Bot.on_message(filters.command('upi') & filters.private)
async def upi_info(bot: Bot, message: Message):
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=PAYMENT_QR,
        caption=PAYMENT_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Contact Owner", url=f"https://t.me/{OWNER}")]]
        )
    )


# -------------------- Callback for "Pay via UPI" button --------------------
@Bot.on_callback_query(filters.regex("upi_info"))
async def upi_button_handler(bot: Bot, query: CallbackQuery):
    await query.answer()
    await bot.send_photo(
        chat_id=query.from_user.id,
        photo=PAYMENT_QR,
        caption=PAYMENT_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Contact Owner", url=f"https://t.me/{OWNER}")]]
        )
    )


# -------------------- /myplan command --------------------
@Bot.on_message(filters.command('myplan') & filters.private)
async def my_plan(bot: Bot, message: Message):
    user_id = message.from_user.id
    plan_status_text = await check_user_plan(user_id)  # Returns info text

    is_premium = await is_premium_user(user_id)

    if is_premium:
        # Extract remaining time from plan_status_text if needed, else just show the text
        response_text = f"✅ Your premium subscription is active.\n\n{plan_status_text}"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Upgrade Plan", callback_data="show_plans")],
            [InlineKeyboardButton("Contact Support", url=f"https://t.me/{OWNER}")]
        ])
    else:
        response_text = f"❌ You are not a premium user.\n\n{plan_status_text}\nView available plans: /plans"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("View Plans", callback_data="show_plans")],
            [InlineKeyboardButton("Contact Support", url=f"https://t.me/{OWNER}")]
        ])

    await message.reply_text(response_text, reply_markup=buttons)


# -------------------- Callback for "show_plans" button in /myplan --------------------
@Bot.on_callback_query(filters.regex("show_plans"))
async def show_plans_callback(bot: Bot, query: CallbackQuery):
    await query.answer()
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Pay via UPI", callback_data="upi_info")],
        [InlineKeyboardButton("Contact Support", url=f"https://t.me/{OWNER}")]
    ])
    await query.message.edit_text(
        text=PAYMENT_TEXT,
        reply_markup=buttons,
        parse_mode=ParseMode.HTML
    )
