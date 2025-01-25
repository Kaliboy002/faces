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
CHANNEL_USERNAME = "@Kali_Linux_BOTS"  # Replace with your channel username (without @)

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
async def start(client, message):
    chat_id = message.chat.id

    # Send a message with two buttons: Join Channel and Check
    keyboard = [
        [InlineKeyboardButton("Join Channel", url=f"t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("Check", callback_data="check_joined")]
    ]

    await client.send_message(
        chat_id,
        "Welcome to the Face Swap Bot! You need to join the channel to continue. Please click 'Join Channel' to join the channel and then click 'Check'.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Callback query handler to check if user joined the channel
@app.on_callback_query(filters.regex("check_joined"))
async def check_joined(client, callback_query):
    chat_id = callback_query.message.chat.id

    # Check if the user has joined the channel
    member = await client.get_chat_member(CHANNEL_USERNAME, chat_id)

    if member.status in ['member', 'administrator', 'creator']:  # If user is a member
        # Update user data to allow usage of the bot
        user_data[chat_id] = {"step": "awaiting_source"}
        await callback_query.message.delete()  # Remove the mandatory message
        await client.send_message(chat_id, "You have successfully joined the channel! Now you can use the bot. Please send the source image (face to swap).")
    else:
        # Inform the user to join the channel
        await client.send_message(chat_id, "You have not joined the channel. Please join the channel first and then click 'Check'.")
        
@app.on_message(filters.photo)
async def handle_photo(client, message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        await client.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = message.photo.file_id
            source_image_path = f"{chat_id}_source.jpg"
            user_data[chat_id]["source_image"] = download_file(client, file_id, source_image_path)
            user_data[chat_id]["step"] = "awaiting_target"
            await client.send_message(chat_id, "Great! Now send the target image (destination face).")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                await client.send_message(chat_id, "Source image is missing. Please restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = message.photo.file_id
            target_image_path = f"{chat_id}_target.jpg"
            user_data[chat_id]["target_image"] = download_file(client, file_id, target_image_path)
            await client.send_message(chat_id, "Processing your request, please wait...")

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
                    await client.send_photo(chat_id, photo=result, caption=f"Face-swapped image: {swapped_image_url}")
                    break

                except Exception as e:
                    await client.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()  # Switch to the next API

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            await client.send_message(chat_id, "Invalid step. Please restart with /start.")
            reset_user_data(chat_id)

    except Exception as e:
        await client.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
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
