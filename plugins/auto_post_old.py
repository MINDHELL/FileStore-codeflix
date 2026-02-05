# (©) Codeflix-Bots | Auto Post Old Videos (FINAL STABLE)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY, ADMINS

PROGRESS_FILE = "autopost_progress.txt"
STOP_FILE = "autopost.stop"


# ─────────── HELPERS ───────────

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


def make_progress_bar(percent, length=20):
    filled = int(length * percent / 100)
    return "█" * filled + "░" * (length - filled)


def is_admin(_, __, message):
    return message.from_user and message.from_user.id in ADMINS


admin_filter = filters.create(is_admin)

# ─────────── COMMANDS ───────────

@Bot.on_message(filters.private & filters.command("stop_autopost") & admin_filter)
async def stop_autopost(_, message):
    with open(STOP_FILE, "w") as f:
        f.write("stop")
    await message.reply("🛑 Auto-post stop requested.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & admin_filter)
async def reset_autopost(_, message):
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    await message.reply(
        "♻️ Auto-post progress reset.\n\n"
        "Next run will start from the FIRST video."
    )


@Bot.on_message(filters.private & filters.command("autopost_old") & admin_filter)
async def autopost_old(client, message):

    # clear old stop flag
    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    status = await message.reply("🚀 Starting auto-post…")

    last_id = load_last_id()
    current = last_id
    posted = 0

    # ── Get total message count safely (last message ID)
    try:
        last_msg = await client.get_messages(SOURCE_CHANNEL, limit=1)
        TOTAL_IDS = last_msg[0].id if last_msg else 1
    except:
        TOTAL_IDS = 1

    while True:

        if stop_requested():
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
                break

            if not msg or not msg.video:
                continue

            try:
                # 1️⃣ Copy video to DB channel
                stored = await msg.copy(
                    chat_id=client.db_channel.id,
                    disable_notification=True
                )

                # 2️⃣ Generate FileStore link (BOT link)
                key = f"get-{stored.id * abs(client.db_channel.id)}"
                token = await encode(key)
                link = f"https://t.me/{client.username}?start={token}"

                caption = (
                    "🎬 New Video Uploaded\n\n"
                    f"🔗 Watch / Download:\n{link}"
                )

                # 3️⃣ Download thumbnail safely
                thumb_path = None
                if msg.video.thumbs:
                    thumb_path = await client.download_media(
                        msg.video.thumbs[0].file_id
                    )

                # 4️⃣ Send thumbnail + caption to TARGET
                if thumb_path:
                    await client.send_photo(
                        chat_id=TARGET_CHANNEL,
                        photo=thumb_path,
                        caption=caption
                    )
                    os.remove(thumb_path)
                else:
                    await client.send_message(
                        chat_id=TARGET_CHANNEL,
                        text=caption
                    )

                save_last_id(msg.id)
                posted += 1

                # ── Progress update every 5 posts
                if posted % 5 == 0:
                    percent = min(int((current / TOTAL_IDS) * 100), 100)
                    bar = make_progress_bar(percent)

                    await status.edit(
                        "🚀 Auto-Posting…\n\n"
                        f"📊 Progress: {bar} {percent}%\n"
                        f"📤 Posted: {posted}\n"
                        f"📌 Current ID: {msg.id}"
                    )

                await asyncio.sleep(AUTO_POST_DELAY)

            except Exception as e:
                await status.edit(f"⚠ Skipped ID {msg.id}\n{e}")
                continue

    # ─────────── FINAL STATUS ───────────

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)
        percent = min(int((current / TOTAL_IDS) * 100), 100)
        bar = make_progress_bar(percent)

        await status.edit(
            "🛑 Auto-post Stopped\n\n"
            f"📊 Progress: {bar} {percent}%\n"
            f"📤 Posted: {posted}"
        )
        return

    await status.edit(
        "✅ Auto-post Finished\n\n"
        "📊 Progress: ████████████████████ 100%\n"
        f"📤 Total Posted: {posted}"
    )
