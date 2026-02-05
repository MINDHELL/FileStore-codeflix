# (©) Codeflix-Bots | Auto Post Old Videos (BOT SAFE FINAL)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY, OWNER_ID

PROGRESS_FILE = "autopost_progress.txt"
DONE_FILE = "posted_ids.txt"
STOP_FILE = "autopost.stop"

BATCH_SIZE = 20


# ---------- Helpers ----------

def load_last_id():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 1


def save_last_id(msg_id):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(msg_id))


def is_done(msg_id):
    if not os.path.exists(DONE_FILE):
        return False
    with open(DONE_FILE, "r") as f:
        return str(msg_id) in f.read().splitlines()


def mark_done(msg_id):
    with open(DONE_FILE, "a") as f:
        f.write(f"{msg_id}\n")


def stop_requested():
    return os.path.exists(STOP_FILE)


# ---------- Admin Commands ----------

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, message):
    open(STOP_FILE, "w").close()
    await message.reply("🛑 Auto-post stopped.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, message):
    for f in [PROGRESS_FILE, DONE_FILE, STOP_FILE]:
        if os.path.exists(f):
            os.remove(f)
    await message.reply("♻️ Auto-post reset.\nWill start from first message.")


# ---------- Auto Post ----------

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    start_id = load_last_id()
    current_id = start_id

    posted = 0
    checked = 0
    found_video_in_run = False

    status = await message.reply(
        f"🚀 Auto-post started\n▶️ From Message ID: {start_id}"
    )

    while True:

        if stop_requested():
            break

        ids = list(range(current_id, current_id + 20))

        try:
            messages = await client.get_messages(SOURCE_CHANNEL, ids)
        except:
            break

        if not messages:
            break

        batch_has_video = False

        for msg in messages:

            current_id += 1

            if stop_requested():
                break

            if not msg:
                continue

            checked += 1

            if not msg.video:
                continue

            batch_has_video = True
            found_video_in_run = True

            # ❗ Skip already posted
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
                    thumb = await client.download_media(
                        msg.video.thumbs[0].file_id
                    )

                if thumb:
                    await client.send_photo(TARGET_CHANNEL, thumb, caption)
                    os.remove(thumb)
                else:
                    await client.send_message(TARGET_CHANNEL, caption)

                mark_done(msg.id)
                save_last_id(msg.id)  # ✅ SAVE ONLY VIDEO ID
                posted += 1

                if posted % 5 == 0:
                    await status.edit(
                        f"🚀 Posting...\n"
                        f"📤 Posted: {posted}\n"
                        f"🆔 Last Video ID: {msg.id}"
                    )

                await asyncio.sleep(AUTO_POST_DELAY)

            except:
                continue

        # ❌ If this batch had NO videos at all → STOP
        if not batch_has_video:
            break

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    # ✅ Proper completion messages
    if not found_video_in_run:
        await status.edit(
            "✅ Auto-post completed\n\n"
            "📭 No new videos found."
        )
    else:
        await status.edit(
            f"✅ Auto-post completed successfully\n\n"
            f"📤 New Videos Posted: {posted}\n"
            f"🔎 Messages Checked: {checked}\n"
            f"🆔 Last Video ID: {load_last_id()}"
    )
