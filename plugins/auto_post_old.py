# (©) Codeflix-Bots | Auto Post Old Videos — FINAL STABLE

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY, OWNER_ID

PROGRESS_FILE = "autopost_progress.txt"
STOP_FILE = "autopost.stop"
DONE_FILE = "posted_ids.txt"


# ─────────── Helpers ───────────

def load_last_id():
    if os.path.exists(PROGRESS_FILE):
        return int(open(PROGRESS_FILE).read().strip())
    return 1


def save_last_id(msg_id):
    open(PROGRESS_FILE, "w").write(str(msg_id))


def stop_requested():
    return os.path.exists(STOP_FILE)


def is_done(msg_id):
    if not os.path.exists(DONE_FILE):
        return False
    return str(msg_id) in open(DONE_FILE).read().splitlines()


def mark_done(msg_id):
    with open(DONE_FILE, "a") as f:
        f.write(f"{msg_id}\n")


# ─────────── Admin Commands ───────────

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, message):
    open(STOP_FILE, "w").close()
    await message.reply("🛑 Auto-post stopped.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, message):
    for f in (PROGRESS_FILE, DONE_FILE, STOP_FILE):
        if os.path.exists(f):
            os.remove(f)

    await message.reply(
        "♻️ Auto-post RESET\n\n"
        "Bot will start again from FIRST video."
    )


# ─────────── Auto Post ───────────

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    current_id = load_last_id()
    posted = 0
    checked = 0
    empty_batches = 0

    status = await message.reply(
        f"🚀 Auto-post started\n▶️ From Message ID: {current_id}"
    )

    while True:

        if stop_requested():
            break

        try:
            ids = list(range(current_id, current_id + 20))
            messages = await client.get_messages(SOURCE_CHANNEL, ids)
        except:
            break

        valid_found = False

        for msg in messages:
            current_id += 1
            save_last_id(current_id)

            if stop_requested():
                break

            if not msg:
                continue

            valid_found = True
            checked += 1

            if not msg.video:
                continue

            if is_done(msg.id):
                continue

            try:
                stored = await msg.copy(client.db_channel.id)

                key = f"get-{stored.id * abs(client.db_channel.id)}"
                token = await encode(key)
                link = f"https://t.me/{client.username}?start={token}"

                caption = (
                    "🎬 <b>New Video Uploaded</b>\n\n"
                    f"🔗 <a href='{link}'>Watch / Download</a>"
                )

                thumb = None
                if msg.video.thumbs:
                    thumb = await client.download_media(msg.video.thumbs[0].file_id)

                if thumb:
                    await client.send_photo(TARGET_CHANNEL, thumb, caption)
                    os.remove(thumb)
                else:
                    await client.send_message(TARGET_CHANNEL, caption)

                mark_done(msg.id)
                posted += 1
                await asyncio.sleep(AUTO_POST_DELAY)

            except:
                continue

        # 🧠 DEAD ID DETECTION
        if not valid_found:
            empty_batches += 1
        else:
            empty_batches = 0

        # 🔁 AUTO RESET WHEN IDs ARE DEAD
        if empty_batches >= 5:
            current_id = 1
            save_last_id(1)
            empty_batches = 0

        if current_id > 5_000_000:
            break

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    await status.edit(
        "✅ Auto-post completed successfully\n\n"
        f"📤 New Videos Posted: {posted}\n"
        f"🔍 Messages Checked: {checked}\n"
        f"🆔 Last ID Scanned: {current_id}"
                )
