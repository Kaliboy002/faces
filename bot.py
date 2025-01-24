import os
import requests
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters
import pymongo
from pymongo import MongoClient
from functools import wraps

# Telegram Bot Token and API Information
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash
BOT_TOKEN = "7844051995:AAGY4U4XSAl7duM5SyaQS2VHecrpGsFQW7w"  # Replace with your Telegram Bot Token
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID
MONGO_URI = "mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/shah?retryWrites=true&w=majority&appName=Cluster0"  # Replace with your MongoDB URI

# Pyrogram Bot Initialization
app = PyroClient("face_swap_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB Client Setup
client = MongoClient(MONGO_URI)
db = client['face_swap_db']
users_collection = db['users']

# List of Gradio Clients for Face Swap APIs
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro"
]
current_client_index = 0
user_data = {}

# Global variable for mandatory subscription
is_subscription_required = True

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

# Language Selection and Subscription Check
def check_subscription(func):
    @wraps(func)
    def wrapper(client, message, *args, **kwargs):
        chat_id = message.chat.id
        user = users_collection.find_one({"chat_id": chat_id})
        if is_subscription_required:
            if user and user.get("subscribed", False):
                return func(client, message, *args, **kwargs)
            else:
                client.send_message(chat_id, "You need to subscribe to use this bot. Please subscribe to our channel.\nبرای استفاده از این ربات باید عضو شوید. لطفا به کانال ما عضو شوید.")
                return
        else:
            return func(client, message, *args, **kwargs)
    return wrapper

@app.on_message(filters.command("start"))
def start(client, message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}

    # Check if user is subscribed
    user = users_collection.find_one({"chat_id": chat_id})
    if user and user.get("subscribed", False):
        client.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).\nبه ربات تغییر چهره خوش آمدید! لطفاً تصویر مبدا (صورت تغییر) را ارسال کنید.")
    else:
        client.send_message(chat_id, "You need to subscribe to use this bot. Please subscribe to our channel.\nبرای استفاده از این ربات باید عضو شوید. لطفا به کانال ما عضو شوید.")

@app.on_message(filters.command("language"))
def language(client, message):
    chat_id = message.chat.id
    client.send_message(chat_id, "Please choose your language:\n1. English\n2. Farsi\n3. Pashto\nلطفاً زبان خود را انتخاب کنید:\n1. انگلیسی\n2. فارسی\n3. پشتو")

@app.on_message(filters.text & filters.regex("1"))
def set_english_language(client, message):
    chat_id = message.chat.id
    users_collection.update_one({"chat_id": chat_id}, {"$set": {"language": "English"}}, upsert=True)
    client.send_message(chat_id, "Language set to English.\nزبان به انگلیسی تغییر یافت.")

@app.on_message(filters.text & filters.regex("2"))
def set_farsi_language(client, message):
    chat_id = message.chat.id
    users_collection.update_one({"chat_id": chat_id}, {"$set": {"language": "Farsi"}}, upsert=True)
    client.send_message(chat_id, "زبان به فارسی تغییر یافت.\nLanguage set to Farsi.")

@app.on_message(filters.text & filters.regex("3"))
def set_pashto_language(client, message):
    chat_id = message.chat.id
    users_collection.update_one({"chat_id": chat_id}, {"$set": {"language": "Pashto"}}, upsert=True)
    client.send_message(chat_id, "زبان په پښتو بدل شو.\nLanguage set to Pashto.")

@app.on_message(filters.command("subscribe"))
def subscribe(client, message):
    chat_id = message.chat.id
    # Add user to the database with subscription status
    users_collection.update_one({"chat_id": chat_id}, {"$set": {"subscribed": True}}, upsert=True)
    client.send_message(chat_id, "Thank you for subscribing! You can now use the bot.\nاز شما برای عضویت تشکر می‌کنیم! اکنون می‌توانید از ربات استفاده کنید.")

@app.on_message(filters.command("unsubscribe"))
def unsubscribe(client, message):
    chat_id = message.chat.id
    # Remove subscription status
    users_collection.update_one({"chat_id": chat_id}, {"$set": {"subscribed": False}}, upsert=True)
    client.send_message(chat_id, "You have unsubscribed. You can no longer use the bot.\nشما لغو عضویت کردید. دیگر نمی‌توانید از ربات استفاده کنید.")

@app.on_message(filters.command("set_subscription"))
def set_subscription(client, message):
    global is_subscription_required
    if message.chat.id == ADMIN_CHAT_ID:
        command = message.text.split()[1] if len(message.text.split()) > 1 else "enable"
        if command == "enable":
            is_subscription_required = True
            client.send_message(ADMIN_CHAT_ID, "Mandatory subscription is now enabled.\nعضویت اجباری اکنون فعال شد.")
        elif command == "disable":
            is_subscription_required = False
            client.send_message(ADMIN_CHAT_ID, "Mandatory subscription is now disabled.\nعضویت اجباری اکنون غیرفعال شد.")
        else:
            client.send_message(ADMIN_CHAT_ID, "Invalid command.\nدستور نامعتبر است.")

@app.on_message(filters.photo)
@check_subscription
def handle_photo(client, message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        client.send_message(chat_id, "Please start the bot using /start.\nلطفاً ربات را با /start شروع کنید.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = message.photo.file_id
            source_image_path = f"{chat_id}_source.jpg"
            user_data[chat_id]["source_image"] = download_file(client, file_id, source_image_path)
            user_data[chat_id]["step"] = "awaiting_target"
            client.send_message(chat_id, "Great! Now send the target image (destination face).\nعالی! حالا تصویر مقصد (صورت مقصد) را ارسال کنید.")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                client.send_message(chat_id, "Source image is missing. Please restart with /start.\nتصویر مبدا گم شده است. لطفاً با /start دوباره شروع کنید.")
                reset_user_data(chat_id)
                return

            file_id = message.photo.file_id
            target_image_path = f"{chat_id}_target.jpg"
            user_data[chat_id]["target_image"] = download_file(client, file_id, target_image_path)
            client.send_message(chat_id, "Processing your request, please wait...\nدر حال پردازش درخواست شما، لطفاً صبر کنید...")

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

                    # Upload the swapped image to Catbox
                    swapped_image_url = upload_to_catbox(result)

                    # Send the swapped image back to the user
                    client.send_photo(chat_id, photo=result, caption=f"Face-swapped image: {swapped_image_url}\nتصویر تغییر یافته صورت: {swapped_image_url}")
                    break

                except Exception as e:
                    client.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()  # Switch to the next API

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            client.send_message(chat_id, "Invalid step. Please restart with /start.\nگام نامعتبر است. لطفاً با /start دوباره شروع کنید.")
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

app.run()
