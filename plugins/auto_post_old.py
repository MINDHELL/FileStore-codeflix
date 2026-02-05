# (©) Codeflix-Bots | Auto Post Old Videos (STABLE FINAL)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY, OWNER_ID

PROGRESS_FILE = "autopost_progress.txt"
DONE_FILE = "posted_ids.txt"
STOP_FILE = "autopost.stop"


# ---------- Helpers ----------

def load_last_id():
    if os.path.exists(PROGRESS_FILE):
        return int(open(PROGRESS_FILE).read().strip())
    return 1


def save_last_id(mid):
    open(PROGRESS_FILE, "w").write(str(mid))


def is_done(mid):
    if not os.path.exists(DONE_FILE):
        return False
    return str(mid) in open(DONE_FILE).read().splitlines()


def mark_done(mid):
    open(DONE_FILE, "a").write(f"{mid}\n")


def stop_requested():
    return os.path.exists(STOP_FILE)


# ---------- Admin Commands ----------

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, msg):
    open(STOP_FILE, "w").close()
    await msg.reply("🛑 Auto-post stopped safely.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, msg):
    for f in [PROGRESS_FILE, DONE_FILE, STOP_FILE]:
        if os.path.exists(f):
            os.remove(f)
    await msg.reply("♻️ Auto-post reset.\nWill start from first video.")


# ---------- Auto Post ----------

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    start_id = load_last_id()
    posted = 0
    checked = 0

    status = await message.reply(
        f"🚀 Auto-post started\n▶️ From ID: {start_id}"
    )

    # 🔥 Get LATEST message ID from channel
    latest = await client.get_messages(SOURCE_CHANNEL, 1)
    if not latest:
        await status.edit("⚠️ Source channel is empty.")
        return

    last_id = latest.id

    current = start_id

    while current <= last_id:

        if stop_requested():
            await status.edit("🛑 Auto-post stopped by admin.")
            return

        try:
            msg = await client.get_messages(SOURCE_CHANNEL, current)
        except:
            current += 1
            continue

        checked += 1
        save_last_id(current)

        if msg and msg.video and not is_done(msg.id):
            try:
                # 1️⃣ Copy to DB
                stored = await msg.copy(client.db_channel.id)

                # 2️⃣ Generate link
                key = f"get-{stored.id * abs(client.db_channel.id)}"
                token = await encode(key)
                link = f"https://t.me/{client.username}?start={token}"

                caption = (
                    "🎬 <b>New Video Uploaded</b>\n\n"
                    f"🔗 <a href='{link}'>Watch / Download</a>"
                )

                # 3️⃣ Thumbnail
                thumb = None
                if msg.video.thumbs:
                    thumb = await client.download_media(
                        msg.video.thumbs[0].file_id
                    )

                # 4️⃣ Send post
                if thumb:
                    await client.send_photo(TARGET_CHANNEL, thumb, caption)
                    os.remove(thumb)
                else:
                    await client.send_message(TARGET_CHANNEL, caption)

                mark_done(msg.id)
                posted += 1

                if posted % 5 == 0:
                    percent = round((current / last_id) * 100, 2)
                    await status.edit(
                        f"🚀 Posting...\n"
                        f"📤 Posted: {posted}\n"
                        f"📊 Progress: {percent}%"
                    )

                await asyncio.sleep(AUTO_POST_DELAY)

            except Exception as e:
                print(e)

        current += 1

    # ✅ ALWAYS SHOW COMPLETION MESSAGE
    await status.edit(
        f"✅ Auto-post completed successfully\n\n"
        f"📤 New Videos Posted: {posted}\n"
        f"🔎 Messages Checked: {checked}\n"
        f"🆔 Last ID Scanned: {last_id}"
    )
