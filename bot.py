import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# Replace these with your own values
API_ID = "15787995"  # Get from https://my.telegram.org
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Get from https://my.telegram.org
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"  # Get from BotFather

# Initialize the Pyrogram Client
app = Client("image_enhancer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# API endpoint
ENHANCE_API = "https://ar-api-08uk.onrender.com/remini"

# Start command
@app.on_message(filters.command("start") & filters.private)
def start(client, message: Message):
    message.reply_text("Hello! Send me an image, and I will enhance it for you.")

# Handle image messages
@app.on_message(filters.photo & filters.private)
def enhance_image(client, message: Message):
    # Notify the user that the image is being processed
    message.reply_text("Processing your image... Please wait.")

    try:
        # Download the image sent by the user
        file_path = message.download()

        # Upload the image to a temporary file hosting service (tmpfiles.org)
        with open(file_path, "rb") as file:
            response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": file})
        
        if response.status_code != 200:
            raise Exception("Failed to upload image to temporary hosting.")

        # Get the temporary file URL from the response
        temp_file_url = response.json()["data"]["url"]

        # Enhance the image using the API
        api_url = f"{ENHANCE_API}?url={temp_file_url}"
        enhance_response = requests.get(api_url)

        if enhance_response.status_code != 200:
            raise Exception("Failed to enhance image.")

        # Parse the enhanced image URL from the API response
        enhanced_image_url = enhance_response.json().get("result")
        if not enhanced_image_url:
            raise Exception("No enhanced image URL found in the API response.")

        # Check if the enhanced image URL is valid
        if not enhanced_image_url.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            raise Exception("Enhanced image URL is not a valid image file.")

        # Send the enhanced image back to the user
        message.reply_photo(enhanced_image_url, caption="Here's your enhanced image!")

    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

    finally:
        # Clean up: Delete the downloaded file
        if os.path.exists(file_path):
            os.remove(file_path)

# Run the bot
print("Bot is running...")
app.run()
