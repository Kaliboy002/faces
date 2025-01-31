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
COOLDOWN_TIME = 30  # seconds

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

def get_text(message_type, language='en'):
    texts = {
        'start': {
            'en': "🤖 Welcome to FaceSwap Bot!\nPlease select your language.",
            'fa': "🤖 خوش آمدید به ربات تغییر چهره!\nلطفا زبان خود را انتخاب کنید."
        },
        'select_lang': {
            'en': "Please select your language:",
            'fa': "لطفا زبان خود را انتخاب کنید:"
        },
        'mandatory': {
            'en': "🔒 You must join our channel to use this bot!\nJoin the channel and click Verify Join to continue.",
            'fa': "🔒 برای استفاده از این ربات باید به کانال ما بپیوندید!\nلطفا به کانال پیوسته و روی دکمه تایید کلیک کنید."
        },
        'verification': {
            'en': "✅ Verification successful! Send source image now.",
            'fa': "✅ تایید با موفقیت انجام شد! عکس منبع خود را ارسال کنید."
        },
        'awaiting_source': {
            'en': "📸 Send the source image (face to swap)",
            'fa': "📸 عکس منبع خود را ارسال کنید (چهرهای میخواهید تغییر دهد)"
        },
        'processing': {
            'en': "⏳ Processing... {}%\nEstimated time: {}s remaining",
            'fa': "⏳ در حال پردازش... {}%\nزمان مقدور: {}s باقی"
        },
        'result': {
            'en': "✨ Face swap completed!\n🔗 URL: {}",
            'fa': "✨ تغییر چهره به اتمام رسید!\n🔗 لینک: {}"
        },
        'cooldown': {
            'en': "⏳ Please wait {} seconds before next swap!",
            'fa': "⏳ لطفا {} ثانیه دیگر از دسترسی خود استفاده کنید!"
        },
        'invalid_input': {
            'en': "📸 Please send photos to face swap!",
            'fa': "📸 لطفا عکس ارسال کنید تا تغییر چهره انجام شود!"
        },
        'error': {
            'en': "⚠️ An error occurred. Please try again.",
            'fa': "⚠️ خطایی پیش آمد. لطفا دوباره تلاش کنید."
        },
        'admin_status': {
            'en': "✅ Mandatory join {} successfully!",
            'fa': "✅ {} اجباری پیوستن با موفقیت انجام شد!"
        },
        'join_channel': {
            'en': "Join Channel",
            'fa': "پیوستن به کانال"
        },
        'verify_join': {
            'en': "Verify Join",
            'fa': "تایید پیوستن"
        }
    }
    return texts[message_type].get(language, 'en')

def show_language_selection(chat_id):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Persian", callback_data="lang_fa")
        ]
    ])
    app.send_message(chat_id, get_text('select_lang', 'en'), reply_markup=keyboard)

def show_mandatory_message(chat_id, language='en'):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text('join_channel', language), url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton(get_text('verify_join', language), callback_data="check_join")]
    ])
    sent = app.send_message(chat_id, get_text('mandatory', language), reply_markup=keyboard)
    user_data[chat_id] = {"mandatory_msg": sent.id, "language": language}

def progress_updater(chat_id, message_id, start_time, language='en'):
    elapsed = 0
    while elapsed < 30:
        try:
            progress = min(elapsed * 3, 100)
            app.edit_message_text(
                chat_id,
                message_id,
                get_text('processing', language).format(progress, 30 - elapsed)
            )
            time.sleep(5)
            elapsed += 5
        except:
            break

def process_face_swap(chat_id, source_path, target_path, language='en'):
    start_time = time.time()
    progress_msg = app.send_message(chat_id, get_text('processing', language).format(0, 30))
    thread = threading.Thread(target=progress_updater, args=(chat_id, progress_msg.id, start_time, language))
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
        return result, result_url
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

    if chat_id in user_data and 'language' in user_data[chat_id]:
        language = user_data[chat_id]['language']
    else:
        language = 'en'

    if not check_membership(user_id):
        show_mandatory_message(chat_id, language)
    else:
        if chat_id not in user_data:
            user_data[chat_id] = {"step": "awaiting_source", "language": language}
        app.send_message(chat_id, get_text('awaiting_source', language))

@app.on_message(filters.command(["on", "off"]) & filters.user(ADMIN_CHAT_ID))
def toggle_mandatory(client, message):
    cmd = message.command[0]
    status = cmd == "on"
    update_mandatory_status(status)
    app.send_message(message.chat.id, get_text('admin_status', 'en').format("enabled" if status else "disabled"))

@app.on_callback_query(filters.regex("^lang_"))
def set_language(client, callback):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    language = callback.data.split('_')[1]

    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['language'] = language

    if callback.message.text == get_text('select_lang', 'en'):
        app.edit_message_text(chat_id, callback.message.id, get_text('start', language))
    else:
        app.delete_messages(chat_id, callback.message.id)
        if not check_membership(user_id):
            show_mandatory_message(chat_id, language)
        else:
            user_data[chat_id]['step'] = 'awaiting_source'
            app.send_message(chat_id, get_text('awaiting_source', language))

@app.on_callback_query(filters.regex("^check_join$"))
def verify_join(client, callback):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    language = user_data.get(chat_id, {}).get('language', 'en')

    if check_membership(user_id):
        app.delete_messages(chat_id, user_data[chat_id]["mandatory_msg"])
        user_data[chat_id]['step'] = 'awaiting_source'
        app.send_message(chat_id, get_text('verification', language))
    else:
        app.answer_callback_query(
            callback.id,
            get_text('mandatory', language),
            show_alert=True
        )

@app.on_message(filters.command("language"))
def language_handler(client, message):
    chat_id = message.chat.id
    show_language_selection(chat_id)

@app.on_message(filters.photo | filters.text)
def main_handler(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    language = user_data.get(chat_id, {}).get('language', 'en')

    if (remaining := check_cooldown(user_id)) > 0:
        app.send_message(chat_id, get_text('cooldown', language).format(remaining))
        return

    if not check_membership(user_id):
        show_mandatory_message(chat_id, language)
        message.delete()
        return

    if not message.photo:
        app.send_message(chat_id, get_text('invalid_input', language))
        return

    if chat_id not in user_data:
        user_data[chat_id] = {"step": "awaiting_source", "language": language}

    try:
        if user_data[chat_id].get("step") == "awaiting_source":
            file_id = message.photo.file_id
            source_path = download_file(client, file_id, f"{chat_id}_source.jpg")
            user_data[chat_id].update({
                "source": source_path,
                "step": "awaiting_target"
            })
            app.send_message(chat_id, get_text('awaiting_target', language))

        elif user_data[chat_id].get("step") == "awaiting_target":
            file_id = message.photo.file_id
            target_path = download_file(client, file_id, f"{chat_id}_target.jpg")

            result_path, result_url = process_face_swap(
                chat_id,
                user_data[chat_id]["source"],
                target_path,
                language
            )

            app.send_photo(
                chat_id, 
                photo=result_path,
                caption=get_text('result', language).format(result_url)
            )

            update_cooldown(user_id)
            os.remove(user_data[chat_id]["source"])
            os.remove(target_path)
            os.remove(result_path)
            del user_data[chat_id]

        else:
            user_data[chat_id] = {"step": "awaiting_source", "language": language}
            app.send_message(chat_id, get_text('awaiting_source', language))

    except Exception as e:
        app.send_message(ADMIN_CHAT_ID, f"❌ Critical Error: {str(e)}")
        if chat_id in user_data:
            if "source" in user_data[chat_id]:
                os.remove(user_data[chat_id]["source"])
            del user_data[chat_id]
        app.send_message(chat_id, get_text('error', language))

if __name__ == "__main__":
    print("🤖 FaceSwap Bot Activated!")
    app.run()
