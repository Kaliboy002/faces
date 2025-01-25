import os
import time
import requests
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters

# Teleتgram Bot Token and API Information
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash
BOT_TOKEN = "7844051995:AAGY4U4XSAl7duM5SyaQS2VHecrpGsFQW7w"  # Replace with your Telegram Bot Token
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID

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

# Cooldown tracking
cooldown_times = {}
language_data = {}

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

def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)

def cleanup_files(chat_id):
    if chat_id in user_data:
        for key in ["source_image", "target_image"]:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])

def get_language_text(chat_id, key):
    language = language_data.get(chat_id, "en")
    if language == "fa":
        return {
            "welcome": "خوش آمدید به ربات تغییر چهره! لطفاً تصویر منبع را ارسال کنید (چهره برای تغییر).",
            "await_target": "عالی! حالا تصویر هدف (چهره مقصد) را ارسال کنید.",
            "processing": "در حال پردازش درخواست شما، لطفاً صبور باشید...",
            "swap_complete": "تصویر تغییر چهره شده: ",
            "wait_for_cooldown": "لطفاً تا تکمیل پردازش تصویر صبر کنید."
        }.get(key, "")
    return {
        "welcome": "Welcome to the Face Swap Bot! Please send the source image (face to swap).",
        "await_target": "Great! Now send the target image (destination face).",
        "processing": "Processing your request, please wait...",
        "swap_complete": "Face-swapped image: ",
        "wait_for_cooldown": "Please wait until the cooldown period is over."
    }.get(key, "")

@app.on_message(filters.command("start"))
def start(client, message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    client.send_message(
        chat_id,
        "Select language:\n1. English\n2. فارسی",
        reply_markup={
            "inline_keyboard": [
                [{"text": "English", "callback_data": "lang_en"}],
                [{"text": "فارسی", "callback_data": "lang_fa"}]
            ]
        }
    )

@app.on_callback_query(filters.regex("lang_"))
def language_selection(client, callback_query):
    chat_id = callback_query.message.chat.id
    lang = callback_query.data.split("_")[1]
    language_data[chat_id] = lang
    client.answer_callback_query(callback_query.id)
    client.send_message(chat_id, get_language_text(chat_id, "welcome"))

@app.on_message(filters.photo)
def handle_photo(client, message):
    chat_id = message.chat.id

    # Cooldown check
    if chat_id in cooldown_times:
        remaining_time = cooldown_times[chat_id] - time.time()
        if remaining_time > 0:
            client.send_message(
                chat_id,
                f"You should wait {int(remaining_time)} seconds before submitting another image."
            )
            return

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
            client.send_message(chat_id, get_language_text(chat_id, "await_target"))

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                client.send_message(chat_id, "Source image is missing. Please restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = message.photo.file_id
            target_image_path = f"{chat_id}_target.jpg"
            user_data[chat_id]["target_image"] = download_file(client, file_id, target_image_path)
            client.send_message(chat_id, get_language_text(chat_id, "processing"))

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
                    client.send_photo(chat_id, photo=result, caption=f"{get_language_text(chat_id, 'swap_complete')}{swapped_image_url}")

                    # Set cooldown time
                    cooldown_times[chat_id] = time.time() + 60  # 60 seconds cooldown

                    break

                except Exception as e:
                    client.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()  # Switch to the next API

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            client.send_message(chat_id, "Invalid step. Please restart with /start.")
            reset_user_data(chat_id)

    except Exception as e:
        client.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)

app.run()
