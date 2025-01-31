import os
import time
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient

# MongoDB Configuration
MONGO_URI = "mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/shah?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["shah"]
settings_collection = db["bot_settings"]
cooldown_collection = db["user_cooldowns"]

# Initialize default settings
if not settings_collection.find_one({"_id": "mandatory_join"}):
    settings_collection.insert_one({
        "_id": "mandatory_join",
        "enabled": True
    })

# Telegram Configuration
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
BOT_TOKEN = "7844051995:AAHTkN2eJswu-CAfe74amMUGok_jaMK0hXQ"
ADMIN_CHAT_ID = 7046488481
CHANNEL_USERNAME = "@Kali_Linux_BOTS"
COOLDOWN_TIME = 80  # seconds

# Pyrogram Bot Initialization
app = PyroClient("face_swap_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# API Configuration with Connection Pooling
api_config = [
    {"url": "Kaliboy0012/face-swapm", "retries": 3},
    {"url": "Jonny0101/Image-Face-Swap", "retries": 3},
    {"url": "kmuti/face-swap", "retries": 3}
]

# Async HTTP Client Session
session = aiohttp.ClientSession()
executor = ThreadPoolExecutor(max_workers=10)
user_data = {}
api_clients = [Client(api["url"]) for api in api_config]

async def get_mandatory_status():
    return settings_collection.find_one({"_id": "mandatory_join"})["enabled"]

async def update_mandatory_status(status: bool):
    settings_collection.update_one(
        {"_id": "mandatory_join"},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def check_cooldown(user_id):
    record = cooldown_collection.find_one({"_id": user_id})
    if record and (time.time() - record["timestamp"]) < COOLDOWN_TIME:
        return int(COOLDOWN_TIME - (time.time() - record["timestamp"]))
    return 0

async def update_cooldown(user_id):
    cooldown_collection.update_one(
        {"_id": user_id},
        {"$set": {"timestamp": time.time()}},
        upsert=True
    )

async def check_membership(user_id):
    if not await get_mandatory_status():
        return True
    try:
        await app.get_chat_member(CHANNEL_USERNAME, user_id)
        return True
    except:
        return False

async def download_file(file_id, save_as):
    try:
        return await app.download_media(file_id, file_name=save_as)
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}")

async def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            async with session.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f}
            ) as response:
                response.raise_for_status()
                return await response.text()
    except Exception as e:
        raise RuntimeError(f"Upload failed: {e}")

async def show_mandatory_message(chat_id):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("Verify Join", callback_data="check_join")]
    ])
    sent = await app.send_message(
        chat_id,
        "🔒 You must join our channel to use this bot!\nJoin the channel and click Verify Join to continue.",
        reply_markup=keyboard
    )
    user_data[chat_id] = {"mandatory_msg": sent.id}

async def process_swap(api, source_path, target_path):
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: api.predict(
                source_file=file(source_path),
                target_file=file(target_path),
                doFaceEnhancer=True,
                api_name="/predict"
            )
        )
        return await upload_to_catbox(result)
    except Exception as e:
        raise RuntimeError(f"API Error: {str(e)}")

async def handle_swap_request(chat_id, source_path, target_path):
    progress_msg = await app.send_message(chat_id, "🚀 Starting face swap...")
    start_time = time.time()
    
    for api in api_clients:
        try:
            result_url = await process_swap(api, source_path, target_path)
            await progress_msg.delete()
            return result_url
        except Exception as e:
            continue
    
    await progress_msg.edit("⚠️ All APIs failed, please try again later")
    raise Exception("All API endpoints failed")

@app.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.delete()
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not await check_membership(user_id):
        await show_mandatory_message(chat_id)
    else:
        user_data[chat_id] = {"step": "awaiting_source"}
        await app.send_message(chat_id, "📸 Send the source image (face to swap)")

@app.on_message(filters.command(["on", "off"]) & filters.user(ADMIN_CHAT_ID))
async def toggle_mandatory(client, message):
    cmd = message.command[0]
    status = cmd == "on"
    await update_mandatory_status(status)
    await message.reply(f"✅ Mandatory join {'enabled' if status else 'disabled'} successfully!")

@app.on_callback_query(filters.regex("^check_join$"))
async def verify_join(client, callback):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    if await check_membership(user_id):
        if chat_id in user_data:
            await app.delete_messages(chat_id, user_data[chat_id]["mandatory_msg"])
        user_data[chat_id] = {"step": "awaiting_source"}
        await callback.answer("✅ Verification successful!")
        await app.send_message(chat_id, "Send source image now.")
    else:
        await callback.answer("❌ You haven't joined the channel!", show_alert=True)

@app.on_message(filters.photo | filters.text)
async def main_handler(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if remaining := await check_cooldown(user_id):
        await message.reply(f"⏳ Please wait {remaining} seconds before next swap!")
        return
    
    if not await check_membership(user_id):
        await show_mandatory_message(chat_id)
        await message.delete()
        return
    
    if not message.photo:
        await message.reply("📸 Please send photos to face swap!")
        return
    
    if chat_id not in user_data:
        user_data[chat_id] = {"step": "awaiting_source"}
    
    try:
        if user_data[chat_id].get("step") == "awaiting_source":
            source_path = await download_file(message.photo.file_id, f"{chat_id}_source.jpg")
            user_data[chat_id].update({"source": source_path, "step": "awaiting_target"})
            await message.reply("🎯 Source image received! Now send target image")
            
        elif user_data[chat_id].get("step") == "awaiting_target":
            target_path = await download_file(message.photo.file_id, f"{chat_id}_target.jpg")
            result_url = await handle_swap_request(chat_id, user_data[chat_id]["source"], target_path)
            
            await app.send_photo(
                chat_id,
                photo=target_path,
                caption=f"✨ Face swap completed!\n🔗 URL: {result_url}"
            )
            await update_cooldown(user_id)
            
            os.remove(user_data[chat_id]["source"])
            os.remove(target_path)
            del user_data[chat_id]
            
    except Exception as e:
        await app.send_message(ADMIN_CHAT_ID, f"❌ Error: {str(e)}")
        if chat_id in user_data:
            if "source" in user_data[chat_id]:
                os.remove(user_data[chat_id]["source"])
            del user_data[chat_id]
        await message.reply("⚠️ An error occurred. Please try again.")

if __name__ == "__main__":
    print("🤖 FaceSwap Bot Activated!")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(app.start())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(app.stop())
        loop.run_until_complete(session.close())
    finally:
        loop.close()
