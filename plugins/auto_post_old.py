# (©) Codeflix-Bots | Auto Post Old Videos (Pyrogram compatible)

import asyncio
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY

PROGRESS_FILE = "autopost_progress.txt"


def load_last_id():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0


def save_last_id(msg_id):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(msg_id))


@Bot.on_message(filters.private & filters.command("autopost_old"))
async def autopost_old(client, message):

    await message.reply("🚀 Auto-posting old videos started...")

    last_id = load_last_id()
    messages = []

    # 1️⃣ Fetch history (newest → oldest)
    async for msg in client.get_chat_history(
        chat_id=SOURCE_CHANNEL,
        offset_id=last_id
    ):
        if msg.video:
            messages.append(msg)

    # 2️⃣ Reverse → oldest → newest
    messages.reverse()

    for msg in messages:
        try:
            # Copy to DB channel
            stored = await msg.copy(
                chat_id=client.db_channel.id,
                disable_notification=True
            )

            # Generate FileStore link
            key = f"get-{stored.id * abs(client.db_channel.id)}"
            base64 = await encode(key)
            link = f"https://t.me/{client.username}?start={base64}"

            caption = (
                "🎬 <b>New Video Uploaded</b>\n\n"
                f"🔗 <a href='{link}'>Watch / Download</a>"
            )

            thumb = msg.video.thumbs[0].file_id if msg.video.thumbs else None

            await client.send_photo(
                chat_id=TARGET_CHANNEL,
                photo=thumb,
                caption=caption,
                parse_mode="html"
            )

            save_last_id(msg.id)
            await asyncio.sleep(AUTO_POST_DELAY)

        except Exception as e:
            await message.reply(f"❌ Error:\n<code>{e}</code>")
            return

    await message.reply("✅ Auto-posting completed successfully.")
