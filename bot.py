import os
import time
import requests
import threading
from queue import Queue
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
COOLDOWN_TIME = 10  # seconds

# Pyrogram Bot Initialization
app = PyroClient("face_swap_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Face Swap API Configuration
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    "kmuti/face-swap"
]

# Create multiple API instances for parallel processing
api_pool = [Client(api) for api in api_clients for _ in range(5)]  # 5 instances per API
api_queue = Queue()
for api in api_pool:
    api_queue.put(api)

# Thread Pool for Parallel Processing
executor = ThreadPoolExecutor(max_workers=20)

# User Data and State Management
user_data = {}

# Language translations
translations = {
    "en": {
        "welcome": "🤖 Face Swap Bot\nPlease select your language.",
        "select_lang": "Please select your language",
        "mandatory_join": "🔒 You must join our channel to use this bot!\nJoin the channel and click Verify Join to continue.",
        "verify_join": "✅ Verification successful! Send source image now.",
        "join_channel": "Join Channel",
        "verify": "Verify Join",
        "source_image": "📸 Send the source image (face to swap)",
        "processing": "⏳ Processing...",
        "processing_complete": "✨ Face swap completed!\n🔗 URL: ",
        "cooldown": "⏳ Please wait {} seconds before next swap!",
        "invalid_input": "📸 Please send photos to face swap!",
        "error": "⚠️ An error occurred. Please try again.",
        "not_joined_alert": "😐 You are not joined. You must join then click on verify.",
        "welcome_caption": "Hi {username}, welcome to Face Swap Bot AI! Please send your main or source photo to proceed.",
        "help_message": "Hi, how are you? You can use this bot for free.",
        "back_button": "Back",
        "change_lang": "Change Language",
        "help_button": "Help"
    },
    "fa": {
        "welcome": "🤖 بات جابه جای چهره\nلطفا زبان خود را انتخاب کنید.",
        "select_lang": "لطفا زبان خود را انتخاب کنید",
        "mandatory_join": "🔒 برای استفاده از این بات باید به کانال ما پیوسته باشید!\nلطفا به کانال پیوسته و روی دکمه تایید کلیک کنید.",
        "verify_join": "✅ تایید با موفقیت انجام شد! عکس منبع خود را ارسال کنید.",
        "join_channel": "پیوستن به کانال",
        "verify": "تایید",
        "source_image": "📸 عکس منبع خود را ارسال کنید",
        "processing": "⏳ در حال پروسیس...",
        "processing_complete": "✨ جابه جای چهره به اتمام رسید!\n🔗 لینک: ",
        "cooldown": "⏳ لطفا {} ثانیه دیگر انتظار دهید!",
        "invalid_input": "📸 لطفا عکس ارسال کنید!",
        "error": "⚠️ خطایی پیش آمد. لطفا دوباره تلاش کنید.",
        "not_joined_alert": "😐 شما عضو نشده‌اید. باید عضو شوید و سپس روی تایید کلیک کنید.",
        "welcome_caption": "سلام {username}، به بات جابه‌جایی چهره خوش آمدید! لطفا عکس اصلی خود را ارسال کنید.",
        "help_message": "سلام، حال شما چطوره؟ شما می‌توانید از این بات به صورت رایگان استفاده کنید.",
        "back_button": "بازگشت",
        "change_lang": "تغییر زبان",
        "help_button": "راهنما"
    }
}

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
        return int(COOLDOWN_TIME - (time.time() - record["timestamp"]))
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

def show_mandatory_message(chat_id, lang="en"):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(translations[lang]["join_channel"], url=f"https://t.me/{CHANNEL_USERNAME[1:]}"),
            InlineKeyboardButton(translations[lang]["verify"], callback_data="check_join")
        ]
    ])
    sent = app.send_message(chat_id, 
        translations[lang]["mandatory_join"],
        reply_markup=keyboard
    )
    user_data[chat_id] = {"mandatory_msg": sent.id, "lang": lang}

def progress_updater(chat_id, message_id, start_time):
    elapsed = 0
    while elapsed < 30:
        try:
            progress = min(elapsed * 3, 100)
            app.edit_message_text(
                chat_id,
                message_id,
                f"{translations[user_data[chat_id]['lang']]['processing']}... {progress}%\nEstimated time: {30 - elapsed}s remaining"
            )
            time.sleep(5)
            elapsed += 5
        except:
            break

def process_face_swap(chat_id, source_path, target_path):
    start_time = time.time()
    lang = user_data[chat_id].get('lang', 'en')
    progress_msg = app.send_message(chat_id, translations[lang]['processing'])
    thread = threading.Thread(target=progress_updater, args=(chat_id, progress_msg.id, start_time))
    thread.start()

    try:
        api = api_queue.get()
        result = api.predict(
            source_file=file(source_path),
            target_file=file(target_path),
            doFaceEnhancer=True,
            api_name="/predict"
        )
        result_url = upload_to_catbox(result)
        app.delete_messages(chat_id, progress_msg.id)
        return result, result_url  # Return both result path and URL
    except Exception as e:
        app.send_message(ADMIN_CHAT_ID, f"⚠️ API Error: {str(e)}")
        raise
    finally:
        api_queue.put(api)
        thread.join()

@app.on_message(filters.command("start"))
def start_handler(client, message):
    message.delete()
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Create language selection keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Persian", callback_data="lang_fa")
        ]
    ])

    # Send welcome message with language selection
    app.send_message(chat_id, translations["en"]["welcome"], reply_markup=keyboard)

@app.on_callback_query(filters.regex("^lang_(en|fa)$"))
def language_callback(client, callback):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    lang = callback.data.split('_')[1]

    # Store selected language in user_data
    user_data[chat_id] = {'lang': lang}

    # Proceed with mandatory join check
    if not check_membership(user_id):
        show_mandatory_message(chat_id, lang)
    else:
        send_welcome_message(chat_id, user_id, lang)

def send_welcome_message(chat_id, user_id, lang):
    # Welcome photo URL
    photo_url = "https://files.catbox.moe/tv24yp.jpg"
    username = app.get_users(user_id).first_name

    # Welcome message with photo and buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translations[lang]["change_lang"], callback_data="change_lang")],
        [InlineKeyboardButton(translations[lang]["help_button"], callback_data="help")]
    ])
    app.send_photo(
        chat_id,
        photo=photo_url,
        caption=translations[lang]["welcome_caption"].format(username=username),
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("^check_join$"))
def verify_join(client, callback):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    lang = user_data.get(chat_id, {}).get('lang', 'en')

    if check_membership(user_id):
        app.delete_messages(chat_id, user_data[chat_id]["mandatory_msg"])
        send_welcome_message(chat_id, user_id, lang)
    else:
        app.answer_callback_query(
            callback.id,
            translations[lang]["not_joined_alert"],
            show_alert=True
        )

@app.on_callback_query(filters.regex("^change_lang$"))
def change_language_callback(client, callback):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    # Create language selection keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Persian", callback_data="lang_fa")
        ]
    ])

    app.send_message(chat_id, translations[user_data.get(chat_id, {}).get('lang', 'en')]["select_lang"], reply_markup=keyboard)

@app.on_callback_query(filters.regex("^help$"))
def help_callback(client, callback):
    chat_id = callback.message.chat.id
    lang = user_data.get(chat_id, {}).get('lang', 'en')

    # Help message with Back button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translations[lang]["back_button"], callback_data="back_to_welcome")]
    ])
    app.send_message(chat_id, translations[lang]["help_message"], reply_markup=keyboard)

@app.on_callback_query(filters.regex("^back_to_welcome$"))
def back_to_welcome_callback(client, callback):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    lang = user_data.get(chat_id, {}).get('lang', 'en')

    # Send welcome message again
    send_welcome_message(chat_id, user_id, lang)

@app.on_message(filters.command(["on", "off"]) & filters.user(ADMIN_CHAT_ID))
def toggle_mandatory(client, message):
    cmd = message.command[0]
    status = cmd == "on"
    update_mandatory_status(status)
    app.send_message(message.chat.id, 
        f"✅ Mandatory join {'enabled' if status else 'disabled'} successfully!"
    )

@app.on_message(filters.photo | filters.text)
def main_handler(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = user_data.get(chat_id, {}).get('lang', 'en')

    if (remaining := check_cooldown(user_id)) > 0:
        app.send_message(chat_id, translations[lang]["cooldown"].format(remaining))
        return

    if not check_membership(user_id):
        show_mandatory_message(chat_id, lang)
        message.delete()
        return

    if not message.photo:
        app.send_message(chat_id, translations[lang]["invalid_input"])
        return

    if chat_id not in user_data:
        user_data[chat_id] = {"step": "awaiting_source", "lang": lang}

    try:
        if user_data[chat_id].get("step") == "awaiting_source":
            file_id = message.photo.file_id
            source_path = download_file(client, file_id, f"{chat_id}_source.jpg")
            user_data[chat_id].update({
                "source": source_path,
                "step": "awaiting_target"
            })
            app.send_message(chat_id, translations[lang]["source_image"])

        elif user_data[chat_id].get("step") == "awaiting_target":
            file_id = message.photo.file_id
            target_path = download_file(client, file_id, f"{chat_id}_target.jpg")

            # Process images and get both result path and URL
            result_path, result_url = process_face_swap(
                chat_id,
                user_data[chat_id]["source"],
                target_path
            )

            # Send the actual swapped image
            app.send_photo(
                chat_id, 
                photo=result_path,  # Send the swapped image file
                caption=f"{translations[lang]['processing_complete']}{result_url}"
            )

            # Update cooldown and cleanup
            update_cooldown(user_id)
            os.remove(user_data[chat_id]["source"])
            os.remove(target_path)
            os.remove(result_path)  # Cleanup the result file
            del user_data[chat_id]

        else:
            user_data[chat_id] = {"step": "awaiting_source", "lang": lang}
            app.send_message(chat_id, translations[lang]["source_image"])

    except Exception as e:
        app.send_message(ADMIN_CHAT_ID, f"❌ Critical Error: {str(e)}")
        if chat_id in user_data:
            if "source" in user_data[chat_id]:
                os.remove(user_data[chat_id]["source"])
            del user_data[chat_id]
        app.send_message(chat_id, translations[lang]["error"])

if __name__ == "__main__":
    print("🤖 FaceSwap Bot Activated!")
    app.run()
