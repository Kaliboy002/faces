import os
import requests
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient

# MongoDB Configuration
MONGO_URI = "mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/shah?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["shah"]
settings_collection = db["bot_settings"]

# Initialize default settings if not exists
if not settings_collection.find_one({"_id": "mandatory_join"}):
    settings_collection.insert_one({
        "_id": "mandatory_join",
        "enabled": True
    })

# Telegram Bot Configuration
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
BOT_TOKEN = "7844051995:AAHTkN2eJswu-CAfe74amMUGok_jaMK0hXQ"
ADMIN_CHAT_ID = 7046488481
CHANNEL_USERNAME = "@Kali_Linux_BOTS"

# Pyrogram Bot Initialization
app = PyroClient("face_swap_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# List of Gradio Clients for Face Swap APIs
api_clients = [
    "Kaliboy0012/face-swapm",
    "Jonny0101/Image-Face-Swap",
    "kmuti/face-swap"
]
current_client_index = 0
user_data = {}

def get_mandatory_status():
    return settings_collection.find_one({"_id": "mandatory_join"})["enabled"]

def update_mandatory_status(status: bool):
    settings_collection.update_one(
        {"_id": "mandatory_join"},
        {"$set": {"enabled": status}},
        upsert=True
    )

def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])

def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)

def download_file(client, file_id, save_as):
    try:
        file_path = client.download_media(file_id, file_name=save_as)
        return file_path
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")

def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f}
            )
            response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Failed to upload file to Catbox: {e}")

@app.on_message(filters.command("start"))
def start(client, message):
    chat_id = message.chat.id
    if get_mandatory_status():
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("Check", callback_data="check_join")]
        ])
        sent_message = message.reply_text(
            "**Mandatory Join**\nYou must join our channel to use this bot!",
            reply_markup=keyboard
        )
        user_data[chat_id] = {"mandatory_message_id": sent_message.id}
    else:
        user_data[chat_id] = {"step": "awaiting_source"}
        message.reply_text("Welcome to the Face Swap Bot! Please send the source image (face to swap).")

@app.on_message(filters.command("off") & filters.user(ADMIN_CHAT_ID))
def disable_mandatory(client, message):
    update_mandatory_status(False)
    message.reply_text("✅ Mandatory channel join disabled. Users can now use the bot without joining.")

@app.on_message(filters.command("on") & filters.user(ADMIN_CHAT_ID))
def enable_mandatory(client, message):
    update_mandatory_status(True)
    message.reply_text("🔒 Mandatory channel join enabled. Users must join channel to use the bot.")

@app.on_callback_query(filters.create(lambda _, __, query: query.data == "check_join"))
def check_join(client, callback_query):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    
    if not get_mandatory_status():
        client.answer_callback_query(
            callback_query.id,
            "ℹ️ Channel verification is currently disabled by admin.",
            show_alert=True
        )
        return

    try:
        client.get_chat_member(CHANNEL_USERNAME, user_id)
        
        if chat_id in user_data and "mandatory_message_id" in user_data[chat_id]:
            client.delete_messages(chat_id, user_data[chat_id]["mandatory_message_id"])
            del user_data[chat_id]["mandatory_message_id"]
        
        user_data[chat_id] = {"step": "awaiting_source"}
        client.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")
        
    except Exception as e:
        client.answer_callback_query(
            callback_query.id,
            "⛔ You haven't joined the channel! Please join and click Check again.",
            show_alert=True
        )
    finally:
        callback_query.answer()

@app.on_message(filters.photo)
def handle_photo(client, message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        client.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = message.photo.file_id
            source_image_path = f"{chat_id}_source.jpg"
            user_data[chat_id]["source_image"] = download_file(client, file_id, source_image_path)
            user_data[chat_id]["step"] = "awaiting_target"
            client.send_message(chat_id, "Great! Now send the target image (destination face).")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                client.send_message(chat_id, "Source image is missing. Please restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = message.photo.file_id
            target_image_path = f"{chat_id}_target.jpg"
            user_data[chat_id]["target_image"] = download_file(client, file_id, target_image_path)
            client.send_message(chat_id, "Processing your request, please wait...")

            # Perform Face Swap
            while True:
                try:
                    client_api = get_client()
                    source_file = user_data[chat_id]["source_image"]
                    target_file = user_data[chat_id]["target_image"]

                    result = client_api.predict(
                        source_file=file(source_file),
                        target_file=file(target_file),
                        doFaceEnhancer=True,
                        api_name="/predict"
                    )

                    swapped_image_url = upload_to_catbox(result)
                    client.send_photo(chat_id, photo=result, caption=f"Face-swapped image: {swapped_image_url}")
                    break

                except Exception as e:
                    client.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            client.send_message(chat_id, "Invalid step. Please restart with /start.")
            reset_user_data(chat_id)

    except Exception as e:
        client.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)

def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)

def cleanup_files(chat_id):
    if chat_id in user_data:
        for key in ["source_image", "target_image"]:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])

if __name__ == "__main__":
    print("🤖 FaceSwap Bot Started!")
    app.run()
