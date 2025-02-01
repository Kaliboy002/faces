import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Telegram Configuration
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API HASH
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"  # Replace with your bot token

# Image Enhancement API URL
ENHANCE_API_URL = "https://i.imghippo.com/files/iDxy5739tZs.jpg"

# Pyrogram Bot Initialization
app = Client("image_enhancer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to download the photo
def download_file(client, file_id, save_as):
    try:
        return client.download_media(file_id, file_name=save_as)
    except Exception as e:
        raise Exception(f"Download failed: {e}")

# Function to call the image enhancement API
def enhance_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            response = requests.post(
                ENHANCE_API_URL,
                files={"file": image_file},
                timeout=10  # Set timeout to 10 seconds
            )
            response.raise_for_status()
            return response.json()  # Return the API response as JSON
    except requests.exceptions.RequestException as e:
        raise Exception(f"API Error: {str(e)}")

# Start command handler
@app.on_message(filters.command("start"))
def start_handler(client, message):
    chat_id = message.chat.id
    app.send_message(
        chat_id,
        "🤖 Welcome to the Image Enhancer Bot!\n\n"
        "Send me a photo, and I'll enhance it for you."
    )

# Photo handler
@app.on_message(filters.photo)
def photo_handler(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Download the photo
    try:
        file_id = message.photo.file_id
        photo_path = download_file(client, file_id, f"{chat_id}_original.jpg")
    except Exception as e:
        app.send_message(chat_id, f"⚠️ Error downloading photo: {str(e)}")
        return

    # Enhance the photo using the API
    try:
        app.send_message(chat_id, "⏳ Enhancing your photo...")
        api_response = enhance_image(photo_path)

        if api_response.get("status") == 200 and api_response.get("result"):
            enhanced_image_url = api_response["result"]
            app.send_photo(chat_id, photo=enhanced_image_url, caption="✨ Here's your enhanced photo!")
        else:
            app.send_message(chat_id, "⚠️ Failed to enhance the photo. Please try again.")
    except Exception as e:
        app.send_message(chat_id, f"⚠️ Error enhancing photo: {str(e)}")
    finally:
        # Clean up the downloaded photo
        if os.path.exists(photo_path):
            os.remove(photo_path)

# Run the bot
if __name__ == "__main__":
    print("🤖 Image Enhancer Bot Activated!")
    app.run()
