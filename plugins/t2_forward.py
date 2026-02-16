# (©) Codeflix-Bots | TARGET ➜ TARGET-2 MANUAL FORWARD SYSTEM

import asyncio
from pyrogram import filters
from bot import Bot
from config import OWNER_ID, DB_URI, DB_NAME, TARGET_CHANNEL, TARGET2_CHANNEL
import motor.motor_asyncio

# ===================== MONGO SETUP =====================

mongo = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
db = mongo[DB_NAME]

progress_col = db["t2_progress"]
control_col  = db["t2_control"]
delay_col    = db["t2_delay"]
sent_col     = db["t2_sent"]


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


async def get_delay():
    data = await delay_col.find_one({"_id": "delay"})
    return data["seconds"] if data else 1800  # default 30 min


async def set_delay(seconds: int):
    await delay_col.update_one(
        {"_id": "delay"},
        {"$set": {"seconds": seconds}},
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


# 🔒 Prevent duplicate sends
async def mark_sent(msg_id: int) -> bool:
    try:
        await sent_col.insert_one({"_id": msg_id})
        return True
    except:
        return False


# ===================== ADMIN COMMANDS =====================

@Bot.on_message(filters.private & filters.command("set_t2_delay") & filters.user(OWNER_ID))
async def cmd_set_delay(_, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: /set_t2_delay 30m | 60m")

    val = message.command[1].lower()

    if val.endswith("m"):
        seconds = int(val[:-1]) * 60
    elif val.endswith("h"):
        seconds = int(val[:-1]) * 3600
    else:
        return await message.reply("❌ Invalid format. Use 30m or 1h")

    await set_delay(seconds)
    await message.reply(f"✅ Delay set to {seconds // 60} minutes")


@Bot.on_message(filters.private & filters.command("start_t2") & filters.user(OWNER_ID))
async def start_t2(client, message):

    await clear_stop()

    last_id = await get_last_id()
    delay = await get_delay()

    status = await message.reply(
        f"🚀 Target ➜ Target-2 started\n"
        f"▶️ From Message ID: {last_id}\n"
        f"⏱ Delay: {delay // 60} min"
    )

    current_id = last_id
    sent = 0
    empty_count = 0  # ✅ stop after 2 missing ids

    while True:

        if await stop_requested():
            break

        try:
            msg = await client.get_messages(TARGET_CHANNEL, current_id)
        except:
            break

        if not msg:
            empty_count += 1
            if empty_count >= 2:
                break
            current_id += 1
            continue

        empty_count = 0  # reset if valid message found

        await set_last_id(current_id)

        if not (msg.text or msg.caption or msg.photo or msg.video or msg.document):
            current_id += 1
            continue

        if not await mark_sent(msg.id):
            current_id += 1
            continue

        try:
            await msg.copy(TARGET2_CHANNEL)
            sent += 1

            await status.edit(
                f"🚀 Forwarding...\n"
                f"📤 Sent: {sent}\n"
                f"🆔 Last ID: {msg.id}"
            )

            delay = await get_delay()  # ✅ dynamic delay
            await asyncio.sleep(delay)

        except:
            pass

        current_id += 1

    await clear_stop()

    await status.edit(
        f"✅ Target ➜ Target-2 stopped\n\n"
        f"📤 Sent: {sent}\n"
        f"🆔 Last Checked ID: {await get_last_id()}"
            )



@Bot.on_message(filters.private & filters.command("stop_t2") & filters.user(OWNER_ID))
async def stop_t2(_, message):
    await request_stop()
    await message.reply("🛑 Target-2 forwarding stopped.")

@Bot.on_message(filters.private & filters.command("start_t2_from_forward") & filters.user(OWNER_ID))
async def start_from_forward(client, message):

    if not message.reply_to_message:
        return await message.reply("❌ Reply to a forwarded post from TARGET channel.")

    fwd = message.reply_to_message

    if not fwd.forward_from_message_id:
        return await message.reply("❌ This is not a forwarded message.")

    start_id = fwd.forward_from_message_id

    await set_last_id(start_id)
    await message.reply(
        f"✅ Starting Target ➜ Target-2 from Message ID: {start_id}\n"
        f"Now run /start_t2"
    )




@Bot.on_message(filters.private & filters.command("reset_t2") & filters.user(OWNER_ID))
async def reset_t2(_, message):
    await progress_col.delete_many({})
    await sent_col.delete_many({})
    await control_col.delete_many({})
    await message.reply(
        "♻️ Target-2 RESET\n\n"
        "▶️ Progress cleared\n"
        "▶️ Sent cache cleared\n"
        "▶️ Will start from FIRST post"
    )
