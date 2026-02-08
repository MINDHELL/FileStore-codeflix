# (©) Codeflix-Bots | Auto Post Old Videos + Delayed Forward (FINAL)

import asyncio
import time
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import (
    SOURCE_CHANNEL,
    TARGET_CHANNEL,
    TARGET_CHANNEL_2,
    AUTO_POST_DELAY,
    DELAY_SECONDS,
    OWNER_ID,
    DB_URI,
    DB_NAME
)

import motor.motor_asyncio

# ===================== MONGO =====================

mongo = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
db = mongo[DB_NAME]

progress_col = db["autopost_progress"]
posted_col   = db["autopost_posted"]
control_col  = db["autopost_control"]
queue_col    = db["target2_queue"]

# ===================== HELPERS =====================

async def get_last_id():
    d = await progress_col.find_one({"_id": "progress"})
    return d["last_id"] if d else 1

async def set_last_id(i):
    await progress_col.update_one(
        {"_id": "progress"},
        {"$set": {"last_id": i}},
        upsert=True
    )

async def stop_requested():
    return await control_col.find_one({"_id": "stop"}) is not None

async def request_stop():
    await control_col.update_one(
        {"_id": "stop"},
        {"$set": {"v": True}},
        upsert=True
    )

async def clear_stop():
    await control_col.delete_one({"_id": "stop"})

async def try_mark_posted(msg_id):
    try:
        await posted_col.insert_one({"_id": msg_id})
        return True
    except:
        return False

# ===================== ADMIN =====================

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, m):
    await request_stop()
    await m.reply("🛑 Auto-post stopped.")

@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, m):
    await progress_col.delete_many({})
    await posted_col.delete_many({})
    await control_col.delete_many({})
    await queue_col.delete_many({})
    await m.reply("♻️ Auto-post + queue RESET")

# ===================== AUTOPOST =====================

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    await clear_stop()

    start = await get_last_id()
    current = start

    posted = 0
    checked = 0
    found_video = False

    no_video_streak = 0
    MAX_NO_VIDEO = 3

    status = await message.reply(
        f"🚀 Auto-post started\n▶️ From Message ID: {start}"
    )

    while True:

        if await stop_requested():
            break

        try:
            msg = await client.get_messages(SOURCE_CHANNEL, current)
        except:
            break

        if not msg:
            break

        checked += 1
        await set_last_id(current)

        if not msg.video:
            no_video_streak += 1
            current += 1
            if no_video_streak >= MAX_NO_VIDEO:
                break
            continue

        no_video_streak = 0
        found_video = True

        if not await try_mark_posted(msg.id):
            current += 1
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
                sent = await client.send_photo(TARGET_CHANNEL, thumb, caption)
            else:
                sent = await client.send_message(TARGET_CHANNEL, caption)

            # ➕ ADD TO TARGET-2 QUEUE
            await queue_col.insert_one({
                "_id": sent.id,
                "from_chat": TARGET_CHANNEL,
                "time": time.time()
            })

            posted += 1
            current += 1
            await asyncio.sleep(AUTO_POST_DELAY)

        except:
            current += 1
            continue

    await clear_stop()

    if not found_video:
        await status.edit("✅ Auto-post completed\n📭 No videos found.")
    else:
        await status.edit(
            f"✅ Auto-post completed\n\n"
            f"📤 Posted: {posted}\n"
            f"🔎 Checked: {checked}\n"
            f"🆔 Last ID: {await get_last_id()}"
        )

# ===================== TARGET-2 WORKER =====================

async def target2_worker(client):
    await asyncio.sleep(5)

    while True:
        doc = await queue_col.find_one({}, sort=[("time", 1)])
        if not doc:
            await asyncio.sleep(10)
            continue

        wait = (doc["time"] + DELAY_SECONDS) - time.time()
        if wait > 0:
            await asyncio.sleep(wait)

        try:
            msg = await client.get_messages(doc["from_chat"], doc["_id"])
            if msg:
                await msg.copy(TARGET_CHANNEL_2)
        except:
            pass

        await queue_col.delete_one({"_id": doc["_id"]})
        await asyncio.sleep(2)

# ===================== START WORKER =====================

@Bot.on_message(filters.command("start"))
async def _start(_, __):
    pass

Bot.add_task(target2_worker)
