# Auto Post Old Videos (Safe + Progress)

import asyncio
import os
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY

PROGRESS_FILE = "autopost_progress.txt"
STOP_FILE = "autopost.stop"


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


@Bot.on_message(filters.private & filters.command("stop_autopost"))
async def stop_autopost(_, message):
    open(STOP_FILE, "w").close()
    await message.reply("🛑 Auto-post stopped.")

@Bot.on_message(filters.private & filters.command("reset_autopost"))
async def reset_autopost(_, message):
    if os.path.exists("autopost_progress.txt"):
        os.remove("autopost_progress.txt")
        await message.reply(
            "♻️ Auto-post progress reset!\n\n"
            "Now the bot will start posting from the FIRST video again."
        )
    else:
        await message.reply(
            "ℹ️ No progress file found.\n"
            "Auto-post will already start from beginning."
        )


@Bot.on_message(filters.private & filters.command("autopost_old"))
async def autopost_old(client, message):

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    last_id = load_last_id()
    posted = 0

    await message.reply("🚀 Auto-post started...")

    # 🔢 Count total videos in source
    total_videos = 0
    async for msg in client.get_chat_history(SOURCE_CHANNEL):
        if msg.video:
            total_videos += 1

    status = await message.reply(
        f"📊 Status\n\n"
        f"🎥 Total videos: {total_videos}\n"
        f"✅ Already posted: {last_id - 1}\n"
        f"⏳ Remaining: {max(total_videos - (last_id - 1), 0)}"
    )

    current = last_id

    while True:

        if stop_requested():
            break

        try:
            msgs = await client.get_messages(
                SOURCE_CHANNEL,
                list(range(current, current + 10))
            )
        except:
            break

        if not msgs:
            break

        for msg in msgs:
            current += 1

            if stop_requested():
                break

            if not msg or not msg.video:
                continue

            try:
                # Store video in DB channel
                stored = await msg.copy(client.db_channel.id)

                # Generate link
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
                    await client.send_photo(TARGET_CHANNEL, thumb, caption=caption)
                    os.remove(thumb)
                else:
                    await client.send_message(TARGET_CHANNEL, caption)

                save_last_id(msg.id)
                posted += 1

                await status.edit(
                    f"📊 Status\n\n"
                    f"🎥 Total videos: {total_videos}\n"
                    f"✅ Posted: {posted}\n"
                    f"⏳ Remaining: {max(total_videos - (last_id - 1) - posted, 0)}"
                )

                await asyncio.sleep(AUTO_POST_DELAY)

            except Exception as e:
                await message.reply(f"⚠ Skipped ID {msg.id}\n<code>{e}</code>")
                continue

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    await message.reply(
        f"✅ Auto-post finished.\n"
        f"📤 Posted: {posted}\n"
        f"⏳ Remaining: {max(total_videos - (last_id - 1) - posted, 0)}"
    )
