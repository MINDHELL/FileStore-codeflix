# (©) Codeflix-Bots | Auto Post Old Videos (SAFE VERSION)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY

PROGRESS_FILE = "autopost_progress.txt"
BATCH_SIZE = 50   # Safe batch (do NOT increase)


def load_last_id():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    return 1


def save_last_id(msg_id):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(msg_id))


@Bot.on_message(filters.private & filters.command("autopost_old"))
async def autopost_old(client, message):
    await message.reply("🚀 Auto-post started safely...")

    last_id = load_last_id()
    posted = 0

    while True:
        try:
            ids = list(range(last_id, last_id + BATCH_SIZE))
            messages = await client.get_messages(SOURCE_CHANNEL, ids)

            video_msgs = [m for m in messages if m and m.video]

            if not video_msgs:
                break

            for msg in video_msgs:
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

                    caption = (
                        "🎬 <b>New Video Uploaded</b>\n\n"
                        f"🔗 <a href='{link}'>Watch / Download</a>"
                    )

                    # 3️⃣ Handle thumbnail safely
                    thumb_path = None
                    if msg.video.thumbs:
                        thumb_path = await client.download_media(
                            msg.video.thumbs[0].file_id
                        )

                    # 4️⃣ Send post to TARGET channel
                    if thumb_path:
                        await client.send_photo(
                            chat_id=TARGET_CHANNEL,
                            photo=thumb_path,
                            caption=caption,
                            parse_mode="html"
                        )
                        os.remove(thumb_path)
                    else:
                        await client.send_message(
                            chat_id=TARGET_CHANNEL,
                            text=caption,
                            parse_mode="html"
                        )

                    save_last_id(msg.id)
                    posted += 1
                    await asyncio.sleep(AUTO_POST_DELAY)

                except Exception as e:
                    await message.reply(f"⚠ Skipped ID {msg.id}\n<code>{e}</code>")
                    continue

            last_id += BATCH_SIZE

        except Exception as e:
            await message.reply(f"❌ Stopped:\n<code>{e}</code>")
            break

    await message.reply(f"✅ Auto-post finished.\n📤 Posted: {posted}")
