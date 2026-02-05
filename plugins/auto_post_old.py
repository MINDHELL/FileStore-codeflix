# (©) Codeflix-Bots | Auto Post Old Videos (FINAL STABLE)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import (SOURCE_CHANNEL,TARGET_CHANNEL,AUTO_POST_DELAY,OWNER_ID)

PROGRESS_FILE = "autopost_progress.txt"
STOP_FILE = "autopost.stop"


# ---------- Progress Helpers ----------

def load_last_id():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 1  # start from first message


def save_last_id(next_id: int):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(next_id))


def stop_requested():
    return os.path.exists(STOP_FILE)


# ---------- Admin Commands ----------

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, message):
    with open(STOP_FILE, "w") as f:
        f.write("stop")
    await message.reply("🛑 Auto-post stopped.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, message):
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        await message.reply(
            "♻️ Auto-post progress RESET.\n\n"
            "Next run will start from the FIRST video."
        )
    else:
        await message.reply("ℹ️ No saved progress found.")


# ---------- Auto-Post Logic ----------

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    current_id = load_last_id()
    posted = 0

    status = await message.reply(
        "🚀 <b>Auto-post started</b>\n"
        f"▶️ Starting from ID: <code>{current_id}</code>",
        quote=True
    )

    while True:

        if stop_requested():
            await status.edit(
                "🛑 <b>Auto-post stopped by admin</b>\n"
                f"📤 Posted: <code>{posted}</code>"
            )
            break

        try:
            ids = list(range(current_id, current_id + 20))
            messages = await client.get_messages(SOURCE_CHANNEL, ids)
        except Exception:
            break

        if not messages:
            break

        progressed = False

        for msg in messages:

            if stop_requested():
                await status.edit(
                    "🛑 <b>Auto-post stopped by admin</b>\n"
                    f"📤 Posted: <code>{posted}</code>"
                )
                return

            if not msg:
                current_id += 1
                save_last_id(current_id)
                continue

            # 🔑 SINGLE SOURCE OF TRUTH
            current_id = msg.id + 1
            save_last_id(current_id)

            if not msg.video:
                continue

            try:
                # 1️⃣ Store video in DB channel
                stored = await msg.copy(client.db_channel.id)

                # 2️⃣ Generate FileStore link
                key = f"get-{stored.id * abs(client.db_channel.id)}"
                token = await encode(key)
                link = f"https://t.me/{client.username}?start={token}"

                caption = (
                    "🎬 <b>Must join @Allvidsbackup3</b>\n\n"
                    f"🔗 <a href='{link}'>Watch / Download</a>"
                )

                # 3️⃣ Download thumbnail safely
                thumb_path = None
                if msg.video.thumbs:
                    thumb_path = await client.download_media(
                        msg.video.thumbs[0].file_id
                    )

                # 4️⃣ Send post
                if thumb_path:
                    await client.send_photo(
                        TARGET_CHANNEL,
                        photo=thumb_path,
                        caption=caption
                    )
                    os.remove(thumb_path)
                else:
                    await client.send_message(
                        TARGET_CHANNEL,
                        caption
                    )

                posted += 1
                progressed = True

                # Live status update
                if posted % 5 == 0:
                    await status.edit(
                        "🚀 <b>Auto-posting...</b>\n\n"
                        f"📤 Posted: <code>{posted}</code>\n"
                        f"➡️ Current ID: <code>{current_id}</code>"
                    )

                await asyncio.sleep(AUTO_POST_DELAY)

            except Exception:
                # Skip safely
                continue

        if not progressed:
            break

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    await status.edit(
        "✅ <b>Auto-post completed</b>\n\n"
        f"📤 Total Posted: <code>{posted}</code>"
            )
