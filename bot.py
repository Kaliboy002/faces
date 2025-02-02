import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# Replace with your bot token
API_ID = 15787995  # Get from https://my.telegram.org
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Get from https://my.telegram.org
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"

# Initialize the Pyrogram client
app = Client("image_enhancer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# API endpoints
PRIMARY_API = "https://ar-api-08uk.onrender.com/remini?url="  # Primary API
FALLBACK_API = "https://api.nyxs.pw/tools/hd?url="  # Fallback API

# Function to upload image to imgbb
def upload_to_imgbb(image_path):
    imgbb_api_key = "b34225445e8edd8349d8a9fe68f20369"  # Replace with your imgbb API key
    upload_url = "https://api.imgbb.com/1/upload"
    try:
        with open(image_path, "rb") as file:
            response = requests.post(upload_url, files={"image": file}, data={"key": imgbb_api_key})
            if response.status_code == 200:
                return response.json()["data"]["url"]
            else:
                print(f"imgBB Upload Failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        print(f"Error uploading to imgBB: {e}")
        return None

# Function to enhance image using APIs
def enhance_image(image_url):
    # Try the primary API first
    try:
        response = requests.get(f"{PRIMARY_API}{image_url}")
        if response.status_code == 200 and response.json().get("status") == 200:
            return response.json()["result"]  # Return enhanced image URL
    except Exception as e:
        print(f"Primary API Failed: {e}")

    # If primary API fails, try the fallback API
    try:
        response = requests.get(f"{FALLBACK_API}{image_url}")
        if response.status_code == 200 and response.json().get("status"):
            return response.json()["result"]  # Return enhanced image URL
    except Exception as e:
        print(f"Fallback API Failed: {e}")

    # If both APIs fail, return None
    return None

# Start command handler
@app.on_message(filters.command("start"))
def start(client: Client, message: Message):
    message.reply_text("Hi! Send me a photo, and I'll enhance it for you.")

# Photo handler
@app.on_message(filters.photo)
def enhance_photo(client: Client, message: Message):
    try:
        # Download the photo
        photo_path = message.download()
        print(f"Photo downloaded to: {photo_path}")

        # Upload the photo to imgBB
        imgbb_url = upload_to_imgbb(photo_path)
        if not imgbb_url:
            message.reply_text("Failed to upload the photo to imgBB. Please try again.")
            return

        print(f"Photo uploaded to imgBB: {imgbb_url}")

        # Enhance the photo using the APIs
        enhanced_url = enhance_image(imgbb_url)
        if enhanced_url:
            print(f"Enhanced photo URL: {enhanced_url}")
            message.reply_photo(enhanced_url, caption="Here's your enhanced photo!")
        else:
            print("Both APIs failed to enhance the photo.")
            message.reply_text("Sorry, both APIs failed to enhance the photo. Please try again later.")

    except Exception as e:
        print(f"Error processing photo: {e}")
        message.reply_text("Sorry, something went wrong while processing your photo.")

    finally:
        # Clean up the downloaded file
        if os.path.exists(photo_path):
            os.remove(photo_path)

# Run the bot
if __name__ == "__main__":
    print("Bot started...")
    app.run()
