import asyncio
from pyrogram import filters
from bot import Bot
from helper_func import encode
from config import SOURCE_CHANNEL, TARGET_CHANNEL, AUTO_POST_DELAY

PROGRESS_FILE = "autopost_progress.txt"
BATCH_SIZE = 50  # safe limit


def load_last_id():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 1


def save_last_id(msg_id):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(msg_id))


@Bot.on_message(filters.private & filters.command("autopost_old"))
async def autopost_old(client, message):

    await message.reply("🚀 Auto-posting old videos started...")

    last_id = load_last_id()
    current_id = last_id

    while True:
        try:
            # ✅ BOT-SAFE message fetch
            ids = list(range(current_id, current_id + BATCH_SIZE))
            messages = await client.get_messages(SOURCE_CHANNEL, ids)

            if not messages:
                break

            for msg in messages:
                if not msg or not msg.video:
                    current_id += 1
                    continue

                # 1️⃣ Copy to DB Channel
                stored = await msg.copy(
                    chat_id=client.db_channel.id,
                    disable_notification=True
                )

                # 2️⃣ Generate FileStore link (ORIGINAL LOGIC)
                key = f"get-{stored.id * abs(client.db_channel.id)}"
                base64 = await encode(key)
                link = f"https://t.me/{client.username}?start={base64}"

                caption = (
                    "🎬 <b>New Video Uploaded</b>\n\n"
                    f"🔗 <a href='{link}'>Watch / Download</a>"
                )

                thumb = (
                    msg.video.thumbs[0].file_id
                    if msg.video.thumbs else None
                )

                # 3️⃣ Post to target channel
                await client.send_photo(
                    chat_id=TARGET_CHANNEL,
                    photo=thumb,
                    caption=caption,
                    parse_mode="html"
                )

                save_last_id(msg.id)
                current_id += 1
                await asyncio.sleep(AUTO_POST_DELAY)

        except Exception as e:
            await message.reply(f"❌ Error:\n<code>{e}</code>")
            return

    await message.reply("✅ Auto-posting completed successfully.")
