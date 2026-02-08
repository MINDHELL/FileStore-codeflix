# (©) Codeflix-Bots | Auto Post Old Videos (MONGO – SINGLE FILE)

import asyncio
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import (SOURCE_CHANNEL,TARGET_CHANNEL,AUTO_POST_DELAY,OWNER_ID,DB_URI,DB_NAME)
from motor.motor_asyncio import AsyncIOMotorClient


# ---------- Mongo Setup ----------

mongo = AsyncIOMotorClient(DB_URI)
db = mongo[DB_NAME]

progress_col = db["autopost_progress"]
posted_col = db["autopost_posted"]
control_col = db["autopost_control"]


# ---------- Mongo Helpers ----------

async def get_last_id():
    data = await progress_col.find_one({"_id": "progress"})
    return data["last_id"] if data else 1


async def set_last_id(msg_id: int):
    await progress_col.update_one(
        {"_id": "progress"},
        {"$set": {"last_id": msg_id}},
        upsert=True
    )


async def is_posted(msg_id: int):
    return bool(await posted_col.find_one({"_id": msg_id}))


async def mark_posted(msg_id: int):
    await posted_col.update_one(
        {"_id": msg_id},
        {"$set": {"posted": True}},
        upsert=True
    )


async def stop_requested():
    data = await control_col.find_one({"_id": "stop"})
    return bool(data and data.get("value"))


async def set_stop(value: bool):
    await control_col.update_one(
        {"_id": "stop"},
        {"$set": {"value": value}},
        upsert=True
    )


async def reset_all():
    await progress_col.delete_many({})
    await posted_col.delete_many({})
    await control_col.delete_many({})


# ---------- Admin Commands ----------

@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, message):
    await set_stop(True)
    await message.reply("🛑 Auto-post stopped.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, message):
    await reset_all()
    await message.reply("♻️ Auto-post reset.\nProgress cleared from MongoDB.")


# ---------- Auto Post Logic ----------

@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):

    await set_stop(False)

    start_id = await get_last_id()
    current_id = start_id

    posted = 0
    checked = 0
    found_video = False

    status = await message.reply(
        f"🚀 Auto-post started\n▶️ From Message ID: {start_id}"
    )

    while True:

        if await stop_requested():
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
            checked += 1

            # 🔒 Always save scan progress
            await set_last_id(current_id)

            if await stop_requested():
                break

            if not msg or not msg.video:
                continue

            batch_has_video = True
            found_video = True

            if await is_posted(msg.id):
                continue

            try:
                stored = await msg.copy(client.db_channel.id)

                key = f"get-{stored.id * abs(client.db_channel.id)}"
                token = await encode(key)
                link = f"https://t.me/{client.username}?start={token}"

                caption = (
                    "🎬 <b>❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️</b>\n\n"
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

                await mark_posted(msg.id)
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

        # ❌ No videos in this batch → stop safely
        if not batch_has_video:
            break

    # ---------- Completion Message ----------

    if not found_video:
        await status.edit(
            "✅ Auto-post completed\n\n"
            "📭 No new videos found."
        )
    else:
        await status.edit(
            f"✅ Auto-post completed successfully\n\n"
            f"📤 New Videos Posted: {posted}\n"
            f"🔎 Messages Checked: {checked}\n"
            f"🆔 Last Scanned ID: {await get_last_id()}"
)
