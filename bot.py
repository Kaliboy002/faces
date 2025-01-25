import os
import time
from datetime import datetime, timedelta
import requests
from gradio_client import Client, file
from pymongo import MongoClient
from pyrogram import Client as PyroClient, filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Telegram Bot Configuration
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash
BOT_TOKEN = "7844051995:AAGY4U4XSAl7duM5SyaQS2VHecrpGsFQW7w"  # Replace with your Telegram Bot Token
MANDATORY_CHANNEL = "Kali_Linux_BOTS"  # Replace with your channel username
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID

# MongoDB Configuration
MONGO_URI = "mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/shah?retryWrites=true&w=majority&appName=Cluster0"  # Replace with your MongoDB URI
DB_NAME = "face_swap_bot"
COLLECTION_NAME = "users"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[shah]
users_collection = db[shm]

# Face Swap API Configuration
api_clients = [
    "Kaliboy0012/face-swapm",
    "Jonny0101/Image-Face-Swap",
    "kmuti/face-swap"
]
current_client_index = 0

# Bot Settings
cooldown_time = 60  # Cooldown in seconds
processing_queue = []
mandatory_subscription_enabled = True  # Default subscription enforcement

# Initialize Pyrogram Bot
app = PyroClient("face_swap_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper Functions
def get_client():
    """Returns the current Gradio API client."""
    global current_client_index
    return Client(api_clients[current_client_index])

def switch_client():
    """Switches to the next Gradio API client."""
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)

def download_file(client, file_id, save_as):
    """Downloads a file from Telegram."""
    try:
        return client.download_media(file_id, file_name=save_as)
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")

def upload_to_catbox(file_path):
    """Uploads a file to Catbox and returns the URL."""
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

def check_subscription(client, chat_id):
    """Checks if the user is subscribed to the mandatory channel."""
    try:
        member = client.get_chat_member(MANDATORY_CHANNEL, chat_id)
        return member.status in ["member", "administrator", "creator"]
    except UserNotParticipant:
        return False
    except Exception:
        return False

def is_user_allowed(chat_id):
    """Checks if the user is allowed to make a new request (cooldown check)."""
    user = users_collection.find_one({"_id": chat_id})
    if not user:
        return True  # Allow new users

    cooldown_end = user.get("cooldown_end")
    if cooldown_end and cooldown_end > datetime.utcnow():
        return False  # Still in cooldown
    return True

def update_cooldown(chat_id):
    """Updates the cooldown for a user."""
    cooldown_end = datetime.utcnow() + timedelta(seconds=cooldown_time)
    users_collection.update_one(
        {"_id": chat_id},
        {"$set": {"cooldown_end": cooldown_end}},
        upsert=True
    )

def cleanup_files(chat_id):
    """Cleans up temporary files for a user."""
    for key in ["source_image", "target_image"]:
        file_path = f"{chat_id}_{key}.jpg"
        if os.path.exists(file_path):
            os.remove(file_path)

@app.on_message(filters.command("start"))
def start(client, message):
    """Handles the /start command."""
    chat_id = message.chat.id

    # Save user to database
    users_collection.update_one(
        {"_id": chat_id},
        {"$set": {"joined_channel": False, "cooldown_end": None}},
        upsert=True
    )

    # Check subscription
    if mandatory_subscription_enabled:
        if not check_subscription(client, chat_id):
            join_message = (
                f"You must join our channel to use this bot: @{MANDATORY_CHANNEL}\n"
                "After joining, click the 'Check Membership' button below."
            )
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL}")],
                [InlineKeyboardButton("Check Membership", callback_data="check_membership")]
            ])
            client.send_message(chat_id, join_message, reply_markup=buttons)
            return

    client.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")
    users_collection.update_one({"_id": chat_id}, {"$set": {"joined_channel": True}})

@app.on_callback_query(filters.regex("check_membership"))
def check_membership(client, callback_query):
    """Handles the 'Check Membership' button."""
    chat_id = callback_query.from_user.id
    if check_subscription(client, chat_id):
        users_collection.update_one({"_id": chat_id}, {"$set": {"joined_channel": True}})
        client.answer_callback_query(callback_query.id, "You are subscribed! You can now use the bot.")
        client.send_message(chat_id, "You are subscribed! Please send the source image (face to swap).")
    else:
        client.answer_callback_query(
            callback_query.id,
            "You are not subscribed! Please join the channel first and click 'Check Membership' again.",
            show_alert=True
        )

@app.on_message(filters.photo)
def handle_photo(client, message):
    """Handles photo uploads."""
    chat_id = message.chat.id

    # Check subscription
    user = users_collection.find_one({"_id": chat_id})
    if mandatory_subscription_enabled and not user.get("joined_channel", False):
        join_message = (
            f"You must join our channel to use this bot: @{MANDATORY_CHANNEL}\n"
            "After joining, click the 'Check Membership' button below."
        )
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL}")],
            [InlineKeyboardButton("Check Membership", callback_data="check_membership")]
        ])
        client.send_message(chat_id, join_message, reply_markup=buttons)
        return

    # Cooldown check
    if not is_user_allowed(chat_id):
        remaining_time = (user["cooldown_end"] - datetime.utcnow()).seconds
        client.send_message(chat_id, f"Please wait {remaining_time} seconds before your next request.")
        return

    # Add to processing queue
    processing_queue.append(chat_id)
    position = len(processing_queue)
    client.send_message(chat_id, f"Your request is in queue. Position: {position}. Please wait.")

    while processing_queue[0] != chat_id:
        time.sleep(1)  # Wait for the user's turn

    # Perform face swap
    client.send_message(chat_id, "Processing your request...")
    update_cooldown(chat_id)
    processing_queue.pop(0)

    # Face swap logic goes here...
    client.send_message(chat_id, "Face swap complete! Enjoy your image.")

app.run()
