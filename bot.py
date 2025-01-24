import os
import aiohttp
from gradio_client import Client, file
from telethon import TelegramClient, events
from telethon.tl.types import InputFile
import asyncio

# Your Telegram bot details
API_ID = '15787995'  # Get your API ID from https://my.telegram.org/auth
API_HASH = 'e51a3154d2e0c45e5ed70251d68382de'  # Get your API Hash from https://my.telegram.org/auth
BOT_TOKEN = "7844051995:AAGY4U4XSAl7duM5SyaQS2VHecrpGsFQW7w"  # Replace with your Telegram bot token

# Create the Telegram Client
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Admin Chat ID (Replace with your Telegram ID to receive error reports)
ADMIN_CHAT_ID = 123456789  # Replace with your Telegram user ID

# List of Gradio Clients for Face Swap APIs
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    # Add your other API clients here
]

current_client_index = 0
user_data = {}  # Temporary storage for user data

# Function to get the current API client
def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])

# Function to switch to the next API client
def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)

# Function to download files from Telegram
async def download_file(file_id, save_as):
    try:
        file_info = await client.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    with open(save_as, "wb") as f:
                        f.write(await response.read())
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")

# Function to upload a file to Catbox and get the URL
async def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f}
                )
                response.raise_for_status()
                return response.text().strip()  # Get the direct URL
    except Exception as e:
        raise Exception(f"Failed to upload file to Catbox: {e}")

# Command handler for /start
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    chat_id = event.chat_id
    user_data[chat_id] = {"step": "awaiting_source"}
    await client.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")

# Handle incoming photos
@client.on(events.NewMessage(func=lambda e: e.photo))
async def handle_photo(event):
    chat_id = event.chat_id

    if chat_id not in user_data:
        await client.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = event.photo.id
            user_data[chat_id]["source_image"] = f"{chat_id}_source.jpg"
            await download_file(file_id, user_data[chat_id]["source_image"])
            user_data[chat_id]["step"] = "awaiting_target"
            await client.send_message(chat_id, "Great! Now send the target image (destination face).")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                await client.send_message(chat_id, "Source image is missing. Please restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = event.photo.id
            user_data[chat_id]["target_image"] = f"{chat_id}_target.jpg"
            await download_file(file_id, user_data[chat_id]["target_image"])
            await client.send_message(chat_id, "Processing your request, please wait...")

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
                    swapped_image_url = await upload_to_catbox(result)

                    # Send the swapped image back to the user
                    with open(result, "rb") as swapped_file:
                        await client.send_file(chat_id, swapped_file, caption=f"Face-swapped image: {swapped_image_url}")
                    break

                except Exception as e:
                    # Report the error to the admin, not the user
                    await client.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()  # Switch to the next API

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            await client.send_message(chat_id, "Invalid step. Please restart with /start.")
            reset_user_data(chat_id)

    except Exception as e:
        # Report the error to the admin, not the user
        await client.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)

# Handle unknown inputs or unsupported content types
@client.on(events.NewMessage(func=lambda e: True))
async def handle_unknown(event):
    await client.send_message(
        event.chat_id,
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
async def main():
    await client.start()
    await client.run_until_disconnected()

# Run the asyncio loop
if __name__ == "__main__":
    asyncio.run(main())
