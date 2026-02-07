# (©) Codeflix-Bots | Auto Post Old Videos (MONGO SAFE)

import asyncio
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY, OWNER_ID
from database.database import *

STOP_FLAG = False


@Bot.on_message(filters.private & filters.command("stop_autopost") & filters.user(OWNER_ID))
async def stop_autopost(_, message):
    global STOP_FLAG
    STOP_FLAG = True
    await message.reply("🛑 Auto-post stopped.")


@Bot.on_message(filters.private & filters.command("reset_autopost") & filters.user(OWNER_ID))
async def reset_autopost(_, message):
    await db.reset_autopost()
    await message.reply("♻️ Auto-post reset.\nProgress cleared from database.")


@Bot.on_message(filters.private & filters.command("autopost_old") & filters.user(OWNER_ID))
async def autopost_old(client, message):
    global STOP_FLAG
    STOP_FLAG = False

    start_id = await db.get_autopost_progress()
    posted = 0
    checked = 0
    found_video = False

    status = await message.reply(
        f"🚀 Auto-post started\n▶️ From Message ID: {start_id}"
    )

    current = start_id

    while not STOP_FLAG:
        ids = list(range(current, current + 20))

        try:
            messages = await client.get_messages(SOURCE_CHANNEL, ids)
        except:
            break

        if not messages:
            break

        batch_has_video = False

        for msg in messages:
            current += 1
            checked += 1

            if STOP_FLAG or not msg or not msg.video:
                continue

            batch_has_video = True
            found_video = True

            if await db.is_video_posted(msg.id):
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
                else:
                    await client.send_message(TARGET_CHANNEL, caption)

                await db.mark_video_posted(msg.id)
                await db.set_autopost_progress(msg.id)

                posted += 1
                await asyncio.sleep(AUTO_POST_DELAY)

            except:
                continue

        if not batch_has_video:
            break

    if not found_video:
        await status.edit("✅ Auto-post completed\n\n📭 No new videos found.")
    else:
        await status.edit(
            f"✅ Auto-post completed successfully\n\n"
            f"📤 Posted: {posted}\n"
            f"🔎 Checked: {checked}\n"
            f"🆔 Last ID: {await db.get_autopost_progress()}"
        )
