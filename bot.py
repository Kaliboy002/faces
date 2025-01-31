import os
import time
import requests
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
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

# API Configuration with Multiple Instances
api_config = [
    {"url": "Kaliboy002/face-swapm", "instances": 3},
    {"url": "Jonny001/Image-Face-Swap", "instances": 3},
    {"url": "kmuti/face-swap", "instances": 3}
]

# Create API Pool with Multiple Instances
api_pool = Queue()
for api in api_config:
    for _ in range(api["instances"]):
        api_pool.put(Client(api["url"]))

# Thread Pool for Parallel Processing
executor = ThreadPoolExecutor(max_workers=15)  # 3 APIs × 5 instances = 15 workers

# User Data and State Management
user_data = {}
active_swaps = set()

def get_mandatory_status():
    return settings_collection.find_one({"_id": "mandatory_join"})["enabled"]

def update_mandatory_status(status: bool):
    settings_collection.update_one(
        {"_id": "mandatory_join"},
        {"$set": {"enabled": status}},
        upsert=True
    )

def check_cooldown(user_id):
    record = cooldown_collection.find_one({"_id": user_id})
    if record and (time.time() - record["timestamp"]) < COOLDOWN_TIME:
        remaining = int(COOLDOWN_TIME - (time.time() - record["timestamp"]))
        return remaining
    return 0

def update_cooldown(user_id):
    cooldown_collection.update_one(
        {"_id": user_id},
        {"$set": {"timestamp": time.time()}},
        upsert=True
    )

def check_membership(user_id):
    if not get_mandatory_status():
        return True
    try:
        app.get_chat_member(CHANNEL_USERNAME, user_id)
        return True
    except:
        return False

def download_file(client, file_id, save_as):
    try:
        return client.download_media(file_id, file_name=save_as)
    except Exception as e:
        raise Exception(f"Download failed: {e}")

def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                files={"fileToUpload": f},
                data={"reqtype": "fileupload"}
            )
            response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Upload failed: {e}")

def show_mandatory_message(chat_id):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("Verify Join", callback_data="check_join")]
    ])
    sent = app.send_message(chat_id, 
        "🔒 You must join our channel to use this bot!\n"
        "Join the channel and click Verify Join to continue.",
        reply_markup=keyboard
    )
    user_data[chat_id] = {"mandatory_msg": sent.id}

async def progress_updater(chat_id, message_id):
    start_time = time.time()
    while time.time() - start_time < 30:
        try:
            elapsed = int(time.time() - start_time)
            remaining = 30 - elapsed
            progress = min(elapsed * 3, 100)
            await app.edit_message_text(
                chat_id,
                message_id,
                f"⚡ Processing... {progress}%\nEstimated time: {remaining}s remaining"
            )
            await asyncio.sleep(5)
        except:
            break

def process_swap_wrapper(chat_id, source_path, target_path):
    try:
        api = api_pool.get()
        result = api.predict(
            source_file=file(source_path),
            target_file=file(target_path),
            doFaceEnhancer=True,
            api_name="/predict"
        )
        return upload_to_catbox(result)
    except Exception as e:
        # Replace faulty API client
        api_pool.put(Client(api.config["url"]))
        raise
    finally:
        api_pool.put(api)

async def handle_swap(chat_id, source_path, target_path):
    progress_msg = await app.send_message(chat_id, "🚀 Starting face swap...")
    asyncio.create_task(progress_updater(chat_id, progress_msg.id))
    
    try:
        loop = asyncio.get_event_loop()
        result_url = await loop.run_in_executor(
            executor,
            process_swap_wrapper,
            chat_id, source_path, target_path
        )
        
        await app.delete_messages(chat_id, progress_msg.id)
        return result_url
    except Exception as e:
        await app.send_message(ADMIN_CHAT_ID, f"⚠️ Swap Error: {str(e)}")
        raise

@app.on_message(filters.command("start"))
def start_handler(client, message):
    message.delete()
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not check_membership(user_id):
        show_mandatory_message(chat_id)
    else:
        user_data[chat_id] = {"step": "awaiting_source"}
        app.send_message(chat_id, "📸 Send the source image (face to swap)")

@app.on_message(filters.command(["on", "off"]) & filters.user(ADMIN_CHAT_ID))
def toggle_mandatory(client, message):
    cmd = message.command[0]
    status = cmd == "on"
    update_mandatory_status(status)
    app.send_message(message.chat.id, 
        f"✅ Mandatory join {'enabled' if status else 'disabled'} successfully!"
    )

@app.on_callback_query(filters.regex("^check_join$"))
def verify_join(client, callback):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    if check_membership(user_id):
        app.delete_messages(chat_id, user_data[chat_id]["mandatory_msg"])
        user_data[chat_id] = {"step": "awaiting_source"}
        app.send_message(chat_id, "✅ Verification successful! Send source image now.")
    else:
        app.answer_callback_query(
            callback.id,
            "❌ You haven't joined the channel!",
            show_alert=True
        )

@app.on_message(filters.photo | filters.text)
def main_handler(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Check cooldown first
    remaining = check_cooldown(user_id)
    if remaining > 0:
        app.send_message(chat_id, f"⏳ Please wait {remaining} seconds before next swap!")
        return
    
    # Mandatory join check
    if not check_membership(user_id):
        show_mandatory_message(chat_id)
        message.delete()
        return
    
    # Handle non-photo messages
    if not message.photo:
        app.send_message(chat_id, "📸 Please send photos to face swap!")
        return
    
    # Initialize user session
    if chat_id not in user_data:
        user_data[chat_id] = {"step": "awaiting_source"}
    
    try:
        if user_data[chat_id].get("step") == "awaiting_source":
            # Handle source image
            file_id = message.photo.file_id
            source_path = download_file(client, file_id, f"{chat_id}_source.jpg")
            user_data[chat_id].update({
                "source": source_path,
                "step": "awaiting_target"
            })
            app.send_message(chat_id, "🎯 Source image received! Now send target image")
            
        elif user_data[chat_id].get("step") == "awaiting_target":
            # Handle target image
            file_id = message.photo.file_id
            target_path = download_file(client, file_id, f"{chat_id}_target.jpg")
            
            # Start async processing
            asyncio.create_task(process_swap(chat_id, user_data[chat_id]["source"], target_path))
            
            # Cleanup
            os.remove(user_data[chat_id]["source"])
            os.remove(target_path)
            del user_data[chat_id]
            
        else:
            user_data[chat_id] = {"step": "awaiting_source"}
            app.send_message(chat_id, "📸 Please start by sending the source image")
            
    except Exception as e:
        app.send_message(ADMIN_CHAT_ID, f"❌ Critical Error: {str(e)}")
        if chat_id in user_data:
            if "source" in user_data[chat_id]:
                os.remove(user_data[chat_id]["source"])
            del user_data[chat_id]
        app.send_message(chat_id, "⚠️ An error occurred. Please try again.")

async def process_swap(chat_id, source_path, target_path):
    try:
        result_url = await handle_swap(chat_id, source_path, target_path)
        await app.send_photo(
            chat_id, 
            photo=target_path,
            caption=f"✨ Face swap completed!\n🔗 URL: {result_url}"
        )
        update_cooldown(chat_id)
    except Exception as e:
        await app.send_message(chat_id, "⚠️ Failed to process swap. Please try again.")

if __name__ == "__main__":
    print("🤖 FaceSwap Bot Activated!")
    app.run()
