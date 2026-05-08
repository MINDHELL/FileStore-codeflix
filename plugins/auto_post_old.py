# (©) Codeflix-Bots | Auto Post Old Videos (STABLE FINAL VERSION)

import asyncio
from pyrogram import filters
from pyrogram.errors import FloodWait
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
posted_col = db["autopost_posted"]
control_col = db["autopost_control"]
delay_col = db["autopost_delay"]

# ===================== HELPERS =====================

async def get_last_id():
    data = await progress_col.find_one({"_id": "progress"})
    return data["last_id"] if data else 0


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


# ===================== DELAY SYSTEM =====================

async def get_delay():
    data = await delay_col.find_one({"_id": "delay"})
    return data["seconds"] if data else AUTO_POST_DELAY


async def set_delay(seconds: int):
    await delay_col.update_one(
        {"_id": "delay"},
        {"$set": {"seconds": seconds}},
        upsert=True
    )


# ===================== DUPLICATE SYSTEM =====================

async def mark_posted(msg_id: int):
    await posted_col.update_one(
        {"_id": msg_id},
        {"$set": {"posted": True}},
        upsert=True
    )


async def already_posted(msg_id: int):
    data = await posted_col.find_one({"_id": msg_id})
    return data is not None


# ===================== STOP COMMAND =====================

@Bot.on_message(
    filters.private
    & filters.command("stop_autopost")
    & filters.user(OWNER_ID)
)
async def stop_autopost(_, message):

    await request_stop()

    await message.reply(
        "🛑 Auto-post stopped."
    )


# ===================== RESET COMMAND =====================

@Bot.on_message(
    filters.private
    & filters.command(["reset_autopost", "restautopost"])
    & filters.user(OWNER_ID)
)
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


# ===================== SET DELAY =====================

@Bot.on_message(
    filters.private
    & filters.command("set_autopost_time")
    & filters.user(OWNER_ID)
)
async def set_autopost_time(_, message):

    if len(message.command) < 2:

        return await message.reply(
            "❌ Usage:\n"
            "/set_autopost_time 20s\n"
            "/set_autopost_time 5m\n"
            "/set_autopost_time 1h"
        )

    val = message.command[1].lower()

    try:

        if val.endswith("s"):
            seconds = int(val[:-1])

        elif val.endswith("m"):
            seconds = int(val[:-1]) * 60

        elif val.endswith("h"):
            seconds = int(val[:-1]) * 3600

        else:
            return await message.reply(
                "❌ Invalid format.\nUse 20s / 5m / 1h"
            )

        await set_delay(seconds)

        await message.reply(
            f"✅ Auto-post delay updated\n\n"
            f"⏱ Delay: {seconds} seconds"
        )

    except Exception as e:

        await message.reply(
            f"❌ Error:\n{e}"
        )


# ===================== AUTO POST =====================

@Bot.on_message(
    filters.private
    & filters.command("autopost_old")
    & filters.user(OWNER_ID)
)
async def autopost_old(client, message):

    await clear_stop()

    last_posted_id = await get_last_id()

    # START CORRECTLY
    if last_posted_id <= 0:
        current_id = 1
    else:
        current_id = last_posted_id + 1

    posted = 0
    checked = 0

    empty_streak = 0
    MAX_EMPTY = 100

    delay = await get_delay()

    status = await message.reply(
        f"🚀 Auto-post started\n"
        f"▶️ From Message ID: {current_id}\n"
        f"⏱ Delay: {delay} sec"
    )

    while True:

        # ================= STOP =================

        if await stop_requested():
            break

        # ================= GET MESSAGE =================

        try:

            msg = await client.get_messages(
                SOURCE_CHANNEL,
                current_id
            )

        except FloodWait as e:

            print(f"FloodWait GET: {e.value}s")

            await asyncio.sleep(e.value)

            continue

        except Exception as e:

            print(f"GET ERROR: {e}")

            current_id += 1
            continue

        # ================= EMPTY IDS =================

        if not msg or msg.empty:

            empty_streak += 1
            current_id += 1

            if empty_streak >= MAX_EMPTY:
                break

            continue

        # valid message found
        empty_streak = 0

        checked += 1

        # ================= ONLY VIDEO/DOCUMENT =================

        if not (msg.video or msg.document):

            current_id += 1
            continue

        # ================= DUPLICATE CHECK =================

        if await already_posted(msg.id):

            current_id += 1
            continue

        stored = None

        try:

            # ================= COPY TO DB =================

            stored = await msg.copy(
                client.db_channel.id
            )

            # ================= CREATE LINK =================

            key = f"get-{stored.id * abs(client.db_channel.id)}"

            token = await encode(key)

            link = (
                f"https://t.me/"
                f"{client.username}?start={token}"
            )

            caption = (
                "🎬 <b>Must Join @Allvidsbackup3</b>\n\n"
                f"🔗 <a href='{link}'>Watch / Download</a>"
            )

            # ================= THUMBNAIL =================

            thumb = None

            try:

                if msg.video and msg.video.thumbs:

                    thumb = await client.download_media(
                        msg.video.thumbs[0].file_id
                    )

                elif msg.document and msg.document.thumbs:

                    thumb = await client.download_media(
                        msg.document.thumbs[0].file_id
                    )

            except Exception as e:

                print(f"THUMB ERROR: {e}")

                thumb = None

            # ================= SEND TO TARGET =================

            try:

                if thumb:

                    await client.send_photo(
                        TARGET_CHANNEL,
                        thumb,
                        caption=caption
                    )

                else:

                    await client.send_message(
                        TARGET_CHANNEL,
                        caption
                    )

            except FloodWait as e:

                print(f"FloodWait SEND: {e.value}s")

                await asyncio.sleep(e.value)

                continue

            # ================= SUCCESS =================

            await mark_posted(msg.id)

            await set_last_id(msg.id)

            posted += 1

            # ================= STATUS =================

            if posted % 5 == 0:

                await status.edit(
                    f"🚀 Posting...\n"
                    f"📤 Posted: {posted}\n"
                    f"🔎 Checked: {checked}\n"
                    f"🆔 Last ID: {msg.id}"
                )

            # ================= DYNAMIC DELAY =================

            delay = await get_delay()

            await asyncio.sleep(delay)

        except Exception as e:

            print(f"POST ERROR: {e}")

            # remove broken db copy
            try:

                if stored:
                    await stored.delete()

            except:
                pass

        current_id += 1

    # ================= CLEANUP =================

    await clear_stop()

    # ================= FINAL STATUS =================

    await status.edit(
        f"✅ Auto-post completed\n\n"
        f"📤 Posted: {posted}\n"
        f"🔎 Checked: {checked}\n"
        f"🆔 Last ID: {await get_last_id()}"
)
