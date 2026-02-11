print("Mega plugin loaded successfully")
import os
import asyncio
import shutil
import logging
from pathlib import Path
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message
from mega import Mega

# ============ CONFIG ============ #

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

OWNER_ID = int(os.environ.get("OWNER_ID", 7437503888))

# ============ LOGGING ============ #

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ INIT ============ #

app = Client(
    "mega-leech-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

mega = Mega()
m = mega.login()  # anonymous login


# ============ HELPERS ============ #

async def download_mega(link: str, user_dir: Path):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: m.download_url(link, str(user_dir))
    )


def cleanup(path: Path):
    if path.exists():
        shutil.rmtree(path)


def get_file_size(file_path: Path):
    return file_path.stat().st_size


# ============ HANDLER ============ #

@app.on_message(filters.regex(r"https?://.*mega\.nz/"))
async def mega_handler(client: Client, message: Message):

    url = message.text.strip()

    if "folder" in url:
        await message.reply("❌ Folder links not supported.")
        return

    status = await message.reply("⏳ Processing...")

    user_dir = DOWNLOAD_DIR / str(message.from_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Get file info
        file_info = m.get_public_url_info(url)
        fsize, fname = file_info.split("|")

        await status.edit("⬇️ Downloading from Mega...")

        start = datetime.now()
        await download_mega(url, user_dir)

        file_path = user_dir / fname

        if not file_path.exists():
            await status.edit("❌ Download failed.")
            cleanup(user_dir)
            return

        await status.edit("⬆️ Uploading to Telegram...")

        await client.send_document(
            chat_id=message.chat.id,
            document=str(file_path),
            caption=f"📁 {fname}"
        )

        end = datetime.now()
        await status.edit(
            f"✅ Done!\n\n"
            f"Download Time: {(end - start).seconds}s"
        )

    except Exception as e:
        logger.exception(e)
        await status.edit("❌ Error occurred. Invalid or expired link.")

    finally:
        cleanup(user_dir)

print("Mega handler triggered")


# ============ RUN ============ #
