import os
import requests
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Telegram Bot Token and API Information
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

# Force Subscribe Configuration
class Config:
    FORCE_SUBSCRIBE = False  # Change to True to force users to subscribe
    CHANNELS = ["Kali_Linux_BOTS"]  # Replace with your actual channel usernames

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

# Check Subscription
def check_subscription(user_id: int):
    states = ['administrator', 'creator', 'member', 'restricted']
    for channel in Config.CHANNELS:
        try:
            api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id=@{channel}&user_id={user_id}"
            response = requests.get(api_url).json()
            if response.get('ok') and response['result']['status'] in states:
                continue
            else:
                return False, channel
        except Exception as e:
            print(f"Error checking membership: {e}")
            return False, channel
    return True, None

@app.on_message(filters.command("start"))
def start(client, message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    client.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")

@app.on_message(filters.photo)
def handle_photo(client, message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        client.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if Config.FORCE_SUBSCRIBE:
            status, channel = check_subscription(message.from_user.id)
            if not status:
                join_message = f"Please join the channel @{channel} to use the bot."
                join_button = InlineKeyboardButton("Join Channel", url=f"https://t.me/{channel}")
                verify_button = InlineKeyboardButton("I Joined", callback_data="check_join")
                client.send_message(chat_id, join_message, reply_markup=InlineKeyboardMarkup([[join_button], [verify_button]]))
                return

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

                    # Upload the swapped image to Catbox
                    swapped_image_url = upload_to_catbox(result)

                    # Send the swapped image back to the user
                    client.send_photo(chat_id, photo=result, caption=f"Face-swapped image: {swapped_image_url}")
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

def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)

def cleanup_files(chat_id):
    if chat_id in user_data:
        for key in ["source_image", "target_image"]:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])

# Toggle Force Subscribe by Admin
@app.on_message(filters.private & filters.user(ADMIN_CHAT_ID) & filters.command("toggle_subscribe"))
async def toggle_force_subscribe(client, message):
    Config.FORCE_SUBSCRIBE = not Config.FORCE_SUBSCRIBE
    status = "enabled" if Config.FORCE_SUBSCRIBE else "disabled"
    await message.reply(f"Force-Subscribe mode has been {status}!")

app.run()
