from pyrogram import filters
from pyrogram.types import Message
from bot import Bot

@Bot.on_message(filters.command("ping") & filters.private)
async def ping_test(client, message: Message):
    await message.reply_text("🏓 Pong! ✅")
