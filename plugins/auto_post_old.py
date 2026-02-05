# (©) Codeflix-Bots | Auto Post Old Videos (START + STOP)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY

PROGRESS_FILE = "autopost_progress.txt"
STOP_FILE = "autopost.stop"


def load_last_id():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 1


def save_last_id(msg_id):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(msg_id))


def stop_requested():
    return os.path.exists(STOP_FILE)


@Bot.on_message(filters.private & filters.command("stop_autopost"))
async def stop_autopost(_, message):
    with open(STOP_FILE, "w") as f:
        f.write("stop")
    await message.reply("🛑 Auto-post stopped successfully.")


@Bot.on_message(filters.private & filters.command("autopost_old"))
async def autopost_old(client, message):

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    await message.reply("🚀 Auto-posting started...")

    last_id = load_last_id()
    posted = 0
    current = last_id

    while True:

        if stop_requested():
            await message.reply(
                f"🛑 Auto-post stopped.\n📤 Posted so far: {posted}"
            )
            break

        try:
            messages = await client.get_messages(
                SOURCE_CHANNEL,
                list(range(current, current + 20))
            )
        except:
            break

        if not messages:
            break

        for msg in messages:
            current += 1

            if stop_requested():
                await message.reply(
                    f"🛑 Auto-post stopped.\n📤 Posted so far: {posted}"
                )
                return

            if not msg or not msg.video:
                continue

            try:
                # 1️⃣ Copy video to DB channel
                stored = await msg.copy(client.db_channel.id)

                # 2️⃣ Generate FileStore link
                key = f"get-{stored.id * abs(client.db_channel.id)}"
                token = await encode(key)
                link = f"https://t.me/{client.username}?start={token}"

                caption = (
                    "🎬 <b>New Video Uploaded</b>\n\n"
                    f"🔗 <a href='{link}'>Watch / Download</a>"
                )

                # 3️⃣ Download thumbnail
                thumb_path = None
                if msg.video.thumbs:
                    thumb_path = await client.download_media(
                        msg.video.thumbs[0].file_id
                    )

                # 4️⃣ Send post to target channel
                if thumb_path:
                    await client.send_photo(
                        TARGET_CHANNEL,
                        photo=thumb_path,
                        caption=caption,
                        parse_mode="HTML"
                    )
                    os.remove(thumb_path)
                else:
                    await client.send_message(
                        TARGET_CHANNEL,
                        caption,
                        parse_mode="HTML"
                    )

                save_last_id(msg.id)
                posted += 1
                await asyncio.sleep(AUTO_POST_DELAY)

            except Exception as e:
                await message.reply(
                    f"⚠ Skipped ID {msg.id}\n<code>{e}</code>"
                )
                continue

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    await message.reply(f"✅ Auto-post finished.\n📤 Total posted: {posted}")
