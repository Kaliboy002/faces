import os
import requests
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Telegram Bot Token and API Information
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash
BOT_TOKEN = "7844051995:AAGY4U4XSAl7duM5SyaQS2VHecrpGsFQW7w"  # Replace with your Telegram Bot Token
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID
MANDATORY_CHANNEL = "Kali_Linux_BOTS"  # Replace with your channel's username (without @)

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
mandatory_subscription_enabled = True  # Default is enabled


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


def check_subscription(client, chat_id):
    try:
        member = client.get_chat_member(MANDATORY_CHANNEL, chat_id)
        return member.status in ["member", "administrator", "creator"]
    except UserNotParticipant:
        return False
    except Exception:
        return False


@app.on_message(filters.command("start"))
def start(client, message):
    chat_id = message.chat.id

    # Check subscription only if it's enabled
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

    user_data[chat_id] = {"step": "awaiting_source"}
    client.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")


@app.on_callback_query(filters.regex("check_membership"))
def check_membership(client, callback_query):
    chat_id = callback_query.from_user.id

    if mandatory_subscription_enabled:
        if check_subscription(client, chat_id):
            # If subscribed, allow access
            client.answer_callback_query(callback_query.id, "You are subscribed! You can now use the bot.")
            user_data[chat_id] = {"step": "awaiting_source"}
            client.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")
        else:
            # If not subscribed, show a warning popup
            client.answer_callback_query(
                callback_query.id,
                "You are not subscribed! Please join the channel first and click 'Check Membership' again.",
                show_alert=True
            )


@app.on_message(filters.photo)
def handle_photo(client, message):
    chat_id = message.chat.id

    # Check subscription only if it's enabled
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


@app.on_message(filters.command("toggle_subscribe") & filters.user(ADMIN_CHAT_ID))
def toggle_subscription(client, message):
    global mandatory_subscription_enabled
    mandatory_subscription_enabled = not mandatory_subscription_enabled
    status = "enabled" if mandatory_subscription_enabled else "disabled"
    client.send_message(ADMIN_CHAT_ID, f"Mandatory subscription has been {status}.")


def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)


def cleanup_files(chat_id):
    if chat_id in user_data:
        for key in ["source_image", "target_image"]:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])


app.run()
