import os
import time
import requests
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from motor.motor_asyncio import AsyncIOMotorClient
from concurrent.futures import ThreadPoolExecutor
from gradio_client import Client as GradioClient, file

# MongoDB Configuration
MONGO_URI = "mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/shah?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["shah"]
settings_collection = db["bot_settings"]
cooldown_collection = db["user_cooldowns"]

# Telegram Configuration
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
BOT_TOKEN = "7844051995:AAHTkN2eJswu-CAfe74amMUGok_jaMK0hXQ"
ADMIN_CHAT_ID = 7046488481
CHANNEL_USERNAME = "@Kali_Linux_BOTS"
COOLDOWN_TIME = 10  # seconds

# Face Swap API Configuration
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    "kmuti/face-swap"
]

# Create multiple API instances for parallel processing
api_pool = [GradioClient(api) for api in api_clients for _ in range(5)]  # 5 instances per API
api_queue = asyncio.Queue()

# Initialize API queue
async def init_api_queue():
    for api in api_pool:
        await api_queue.put(api)

# Create executor for file operations
executor = ThreadPoolExecutor(max_workers=20)

# User Data and State Management
user_data = {}

# Initialize Pyrogram bot
app = Client("face_swap_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database functions
async def get_mandatory_status():
    result = await settings_collection.find_one({"_id": "mandatory_join"})
    return result.get("enabled", True)

async def update_mandatory_status(status: bool):
    await settings_collection.update_one(
        {"_id": "mandatory_join"},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def check_cooldown(user_id):
    result = await cooldown_collection.find_one({"_id": user_id})
    if result:
        elapsed = time.time() - result["timestamp"]
        if elapsed < COOLDOWN_TIME:
            return int(COOLDOWN_TIME - elapsed)
    return 0

async def update_cooldown(user_id):
    await cooldown_collection.update_one(
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

# File operations
async def download_file(client, file_id, save_as):
    return await executor.submit(
        client.download_media,
        file_id,
        file_name=save_as
    )

async def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            response = await asyncio.to_thread(
                requests.post,
                "https://catbox.moe/user/api.php",
                files={"fileToUpload": f},
                data={"reqtype": "fileupload"}
            )
            response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Upload failed: {e}")

# Progress updater
async def progress_updater(chat_id, message_id, start_time):
    elapsed = 0
    while elapsed < 30:
        try:
            progress = min(elapsed * 3, 100)
            await app.edit_message_text(
                chat_id,
                message_id,
                f"⏳ Processing... {progress}%\nEstimated time: {30 - elapsed}s remaining"
            )
            await asyncio.sleep(5)
            elapsed += 5
        except:
            break

# Face swap processing
async def process_face_swap(chat_id, source_path, target_path):
    api = await api_queue.get()
    try:
        result = await asyncio.to_thread(
            api.predict,
            source_file=file(source_path),
            target_file=file(target_path),
            doFaceEnhancer=True,
            api_name="/predict"
        )
        result_url = await upload_to_catbox(result)
        return result, result_url
    except Exception as e:
        await app.send_message(ADMIN_CHAT_ID, f"⚠️ API Error: {str(e)}")
        raise
    finally:
        await api_queue.put(api)

# Bot handlers
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
    await app.send_message(message.chat.id, 
        f"✅ Mandatory join {'enabled' if status else 'disabled'} successfully!"
    )

async def show_mandatory_message(chat_id):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("Verify Join", callback_data="check_join")]
    ])
    sent = await app.send_message(chat_id, 
        "🔒 You must join our channel to use this bot!\nJoin the channel and click Verify Join to continue.",
        reply_markup=keyboard
    )
    user_data[chat_id] = {"mandatory_msg": sent.id}

@app.on_callback_query(filters.regex("^check_join$"))
async def verify_join(client, callback):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if await check_membership(user_id):
        await app.delete_messages(chat_id, user_data[chat_id]["mandatory_msg"])
        user_data[chat_id] = {"step": "awaiting_source"}
        await app.send_message(chat_id, "✅ Verification successful! Send source image now.")
    else:
        await app.answer_callback_query(
            callback.id,
            "❌ You haven't joined the channel!",
            show_alert=True
        )

@app.on_message(filters.photo | filters.text)
async def main_handler(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if (remaining := await check_cooldown(user_id)) > 0:
        await app.send_message(chat_id, f"⏳ Please wait {remaining} seconds before next swap!")
        return

    if not await check_membership(user_id):
        await show_mandatory_message(chat_id)
        await message.delete()
        return

    if not message.photo:
        await app.send_message(chat_id, "📸 Please send photos to face swap!")
        return

    if chat_id not in user_data:
        user_data[chat_id] = {"step": "awaiting_source"}

    try:
        if user_data[chat_id].get("step") == "awaiting_source":
            file_id = message.photo.file_id
            source_path = await download_file(client, file_id, f"{chat_id}_source.jpg")
            user_data[chat_id].update({
                "source": source_path,
                "step": "awaiting_target"
            })
            await app.send_message(chat_id, "🎯 Source image received! Now send target image")

        elif user_data[chat_id].get("step") == "awaiting_target":
            file_id = message.photo.file_id
            target_path = await download_file(client, file_id, f"{chat_id}_target.jpg")

            # Process images and both result path and URL
            result_path, result_url = await process_face_swap(
                chat_id,
                user_data[chat_id]["source"],
                target_path
            )

            # Send the actual swapped image
            await app.send_photo(
                chat_id, 
                photo=result_path,  # Send the swapped image file
                caption=f"✨ Face swap completed!\n🔗 URL: {result_url}"
            )

            # Update cooldown and cleanup
            await update_cooldown(user_id)
            os.remove(user_data[chat_id]["source"])
            os.remove(target_path)
            os.remove(result_path)  # Cleanup the result file
            del user_data[chat_id]

        else:
            user_data[chat_id] = {"step": "awaiting_source"}
            await app.send_message(chat_id, "📸 Please start by sending the source image")

    except Exception as e:
        await app.send_message(ADMIN_CHAT_ID, f"❌ Critical Error: {str(e)}")
        if chat_id in user_data:
            if "source" in user_data[chat_id]:
                os.remove(user_data[chat_id]["source"])
            del user_data[chat_id]
        await app.send_message(chat_id, "⚠️ An error occurred. Please try again.")

# Main function
async def main():
    await app.start()
    await init_api_queue()
    print("🤖 FaceSwap Bot Activated!")
    await app.idle()

if __name__ == "__main__":
    asyncio.run(main())
