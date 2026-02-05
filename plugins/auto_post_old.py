# (©) Codeflix-Bots | Auto Post Old Videos (FINAL — FIXED)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY, OWNER_ID

PROGRESS_FILE = "autopost_progress.txt"
STOP_FILE = "autopost.stop"
DONE_FILE = "posted_ids.txt"

BATCH_SIZE = 20


# ---------- Helpers ----------

def load_last_id():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0   # IMPORTANT: start from 0, not 1


def save_last_id(msg_id):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(msg_id))


def stop_requested():
    return os.path.exists(STOP_FILE)


def is_done(msg_id):
    if not os.path.exists(DONE_FILE):
        return False
    with open(DONE_FILE, "r") as f:
        return str(msg_id) in f.read().splitlines()


def mark_done(msg_id):
    with open(DONE_FILE, "a") as f:
        f.write(f"{msg_id}\n")


# ---------- Admin Commands ----------

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, message):
    open(STOP_FILE, "w").close()
    await message.reply("🛑 Auto-post stopped.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, message):
    for f in [PROGRESS_FILE, DONE_FILE]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    await message.reply("♻️ Auto-post RESET.\nWill start from first video again.")


# ---------- Auto Post ----------

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    last_id = load_last_id()
    posted = 0
    checked = 0
    max_id = last_id

    status = await message.reply(
        f"🚀 Auto-post started\n▶️ From Message ID: {last_id}"
    )

    while True:

        if stop_requested():
            break

        try:
            # ✅ CORRECT WAY
            messages = await client.get_messages(
                SOURCE_CHANNEL,
                offset_id=last_id,
                limit=20
            )
        except Exception as e:
            break

        if not messages:
            break  # real completion

        for msg in messages:

            if stop_requested():
                break

            if not msg:
                continue

            checked += 1
            max_id = max(max_id, msg.id)

            if not msg.video:
                continue

            if is_done(msg.id):
                continue

            try:
                # 1️⃣ Copy to DB channel
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
                    await status.edit(
                        f"🚀 Posting...\n"
                        f"📤 Posted: {posted}\n"
                        f"🆔 Last ID: {max_id}"
                    )

                await asyncio.sleep(AUTO_POST_DELAY)

            except:
                continue

        # ✅ MOVE FORWARD SAFELY
        last_id = max_id
        save_last_id(last_id)

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    await status.edit(
        f"✅ Auto-post completed successfully\n\n"
        f"📤 New Videos Posted: {posted}\n"
        f"🔎 Messages Checked: {checked}\n"
        f"🆔 Last ID Scanned: {last_id}"
                    )
