import telebot
import requests
from gradio_client import Client, file
import os

# Telegram Bot Token
BOT_TOKEN = "7844051995:AAG0yvKGMjwHCajxDmzN6O47rcjd4SOzJOw"  # Replace with your Telegram bot token
bot = telebot.TeleBot(BOT_TOKEN)

# Admin Chat ID (Replace with your Telegram ID to receive error reports)
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID

# List of Gradio Clients for Face Swap APIs
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro",
    "mrbeliever/Face-Swapper",
    "Alibrown/Advanced-Face-Swaper",
    "kmuti/face-swap",
    "Karthik64001/Face-Swap",
    "muzammil-altaf/face-swap-pro",
    "bep40/Face-Swap-Roop",
    "HelloSun/Face-Swap-Roop",
    "mukaist/face-swap-pro",
    "haydenbanz/Hades-face-swap",
    "Greff3/Face-Swap-Roop",
    "andyaii/face-swap-new",
    "lalashechka/face-swap",
    "m-ric/Face-Swap-Roop",
    "MartsoBodziu1994/face-swap",
    "Morta57/face-swap",
    "benner3000/AI-MASTERCLASS-FACE-SWAP",
    "nirajandhakal/Good-Face-Swap",
    "peterpeter8585/face-swap"
]

current_client_index = 0
user_data = {}  # Temporary storage for user data


def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])


# Function to switch to the next API client
def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)


# Function to download files from Telegram
def download_file(file_id, save_as):
    try:
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        response = requests.get(file_url, stream=True)
        with open(save_as, "wb") as f:
            f.write(response.content)
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")


# Function to upload a file to Catbox and get the URL
def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f}
            )
            response.raise_for_status()
            return response.text.strip()  # Get the direct URL
    except Exception as e:
        raise Exception(f"Failed to upload file to Catbox: {e}")


# Start command handler
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    bot.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")


# Handle photos sent by the user
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.chat.id

    if chat_id not in user_data:
        bot.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = message.photo[-1].file_id
            user_data[chat_id]["source_image"] = f"{chat_id}_source.jpg"
            download_file(file_id, user_data[chat_id]["source_image"])
            user_data[chat_id]["step"] = "awaiting_target"
            bot.send_message(chat_id, "Great! Now send the target image (destination face).")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                bot.send_message(chat_id, "Source image is missing. Please restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = message.photo[-1].file_id
            user_data[chat_id]["target_image"] = f"{chat_id}_target.jpg"
            download_file(file_id, user_data[chat_id]["target_image"])
            bot.send_message(chat_id, "Processing your request, please wait...")

            # Perform Face Swap
            while True:
                try:
                    client = get_client()
                    source_file = user_data[chat_id]["source_image"]
                    target_file = user_data[chat_id]["target_image"]

                    result = client.predict(
                        source_file=file(source_file),
                        target_file=file(target_file),
                        doFaceEnhancer=True,
                        api_name="/predict"
                    )

                    # Upload the swapped image to Catbox
                    swapped_image_url = upload_to_catbox(result)

                    # Send the swapped image back to the user
                    with open(result, "rb") as swapped_file:
                        bot.send_photo(chat_id, swapped_file, caption=f"Face-swapped image: {swapped_image_url}")
                    break

                except Exception as e:
                    # Report the error to the admin, not the user
                    bot.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()  # Switch to the next API

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            bot.send_message(chat_id, "Invalid step. Please restart with /start.")
            reset_user_data(chat_id)

    except Exception as e:
        # Report the error to the admin, not the user
        bot.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)


# Handle unknown inputs or unsupported content types
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.send_message(
        message.chat.id,
        "I didn't understand that. Please send an image or use /start to begin."
    )


# Helper function to reset user data
def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)


# Helper function to clean up files
def cleanup_files(chat_id):
    if chat_id in user_data:
        for key in ["source_image", "target_image"]:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])


# Run the bot
bot.polling()
