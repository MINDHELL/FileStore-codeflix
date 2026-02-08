# (©) Codeflix-Bots | Auto Post Old Videos (FINAL • MONGO • SMART STOP)

import asyncio
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import (
    SOURCE_CHANNEL,
    TARGET_CHANNEL,
    AUTO_POST_DELAY,
    OWNER_ID,
    DB_URI,
    DB_NAME
)

import motor.motor_asyncio

# ===================== MONGO SETUP =====================

mongo = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
db = mongo[DB_NAME]

progress_col = db["autopost_progress"]
posted_col   = db["autopost_posted"]
control_col  = db["autopost_control"]


# ===================== HELPERS =====================

async def get_last_id():
    data = await progress_col.find_one({"_id": "progress"})
    return data["last_id"] if data else 1


async def set_last_id(msg_id: int):
    await progress_col.update_one(
        {"_id": "progress"},
        {"$set": {"last_id": msg_id}},
        upsert=True
    )


async def stop_requested():
    return await control_col.find_one({"_id": "stop"}) is not None


async def request_stop():
    await control_col.update_one(
        {"_id": "stop"},
        {"$set": {"value": True}},
        upsert=True
    )


async def clear_stop():
    await control_col.delete_one({"_id": "stop"})


# 🔒 Prevent duplicate posts (atomic)
async def try_mark_posted(msg_id: int) -> bool:
    try:
        await posted_col.insert_one({"_id": msg_id})
        return True
    except:
        return False


# ===================== ADMIN COMMANDS =====================

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, message):
    await request_stop()
    await message.reply("🛑 Auto-post stopped.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, message):
    await progress_col.delete_many({})
    await posted_col.delete_many({})
    await control_col.delete_many({})
    await message.reply(
        "♻️ Auto-post RESET\n\n"
        "▶️ Progress cleared\n"
        "▶️ Duplicate cache cleared\n"
        "▶️ Will start from FIRST message"
    )


# ===================== AUTO POST =====================

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    await clear_stop()

    start_id = await get_last_id()
    current_id = start_id

    posted = 0
    checked = 0
    found_video = False

    no_video_streak = 0          # 🔑 IMPORTANT
    MAX_NO_VIDEO = 2             # stop after 3 empty IDs

    status = await message.reply(
        f"🚀 Auto-post started\n"
        f"▶️ From Message ID: {start_id}"
    )

    while True:

        if await stop_requested():
            break

        try:
            msg = await client.get_messages(SOURCE_CHANNEL, current_id)
        except:
            break

        if not msg:
            break

        checked += 1
        await set_last_id(current_id)

        # ❌ NO VIDEO
        if not msg.video:
            no_video_streak += 1
            current_id += 1

            if no_video_streak >= MAX_NO_VIDEO:
                break

            continue

        # ✅ VIDEO FOUND → RESET STREAK
        no_video_streak = 0
        found_video = True

        # 🔒 Skip if already posted
        if not await try_mark_posted(msg.id):
            current_id += 1
            continue

        try:
            stored = await msg.copy(client.db_channel.id)

            key = f"get-{stored.id * abs(client.db_channel.id)}"
            token = await encode(key)
            link = f"https://t.me/{client.username}?start={token}"

            caption = (
                "🎬 <b>Must Join @Allvidsbackup3</b>\n\n"
                f"🔗 <a href='{link}'>Watch / Download</a>"
            )

            thumb = None
            if msg.video.thumbs:
                thumb = await client.download_media(msg.video.thumbs[0].file_id)

            if thumb:
                await client.send_photo(TARGET_CHANNEL, thumb, caption)
            else:
                await client.send_message(TARGET_CHANNEL, caption)

            posted += 1
            current_id += 1

            if posted % 5 == 0:
                await status.edit(
                    f"🚀 Posting...\n"
                    f"📤 Posted: {posted}\n"
                    f"🆔 Last ID: {msg.id}"
                )

            await asyncio.sleep(AUTO_POST_DELAY)

        except:
            current_id += 1
            continue

    await clear_stop()

    # ===================== FINAL MESSAGE =====================

    if not found_video:
        await status.edit(
            "✅ Auto-post completed\n\n"
            "📭 No videos found."
        )
    else:
        await status.edit(
            f"✅ Auto-post completed successfully\n\n"
            f"📤 New Videos Posted: {posted}\n"
            f"🔎 Messages Checked: {checked}\n"
            f"🆔 Last Message ID: {await get_last_id()}"
)
