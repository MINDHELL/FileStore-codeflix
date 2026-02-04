# (©) Codexbotz style – Auto Post Old Videos

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

    await message.reply("🚀 Starting auto-posting of old videos...")

    last_id = load_last_id()

    async for msg in client.get_chat_history(
        chat_id=SOURCE_CHANNEL,
        offset_id=last_id,
        reverse=True
    ):
        if not msg.video:
            continue

        try:
            # 1️⃣ Copy video to DB channel
            stored = await msg.copy(
                chat_id=client.db_channel.id,
                disable_notification=True
            )

            # 2️⃣ Generate FileStore link
            key = f"get-{stored.id * abs(client.db_channel.id)}"
            base64 = await encode(key)
            link = f"https://t.me/{client.username}?start={base64}"

            # 3️⃣ Caption
            caption = (
                "🎬 <b>New Video Uploaded</b>\n\n"
                f"🔗 <a href='{link}'>Watch / Download</a>"
            )

            # 4️⃣ Thumbnail
            thumb = msg.video.thumbs[0].file_id if msg.video.thumbs else None

            # 5️⃣ Post to target channel
            await client.send_photo(
                chat_id=TARGET_CHANNEL,
                photo=thumb,
                caption=caption,
                parse_mode="html"
            )

            save_last_id(msg.id)
            await asyncio.sleep(AUTO_POST_DELAY)

        except Exception as e:
            await message.reply(f"❌ Error occurred:\n<code>{e}</code>")
            return

    await message.reply("✅ Auto-posting completed.")
