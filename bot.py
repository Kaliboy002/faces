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

# API endpoint
ENHANCE_API = "https://api.nyxs.pw/tools/hd?url="

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

        # Enhance the photo using the API
        enhance_response = requests.get(f"{ENHANCE_API}{imgbb_url}")
        if enhance_response.status_code == 200:
            enhanced_url = enhance_response.json()["result"]
            print(f"Enhanced photo URL: {enhanced_url}")

            # Send the enhanced photo back to the user
            message.reply_photo(enhanced_url, caption="Here's your enhanced photo!")
        else:
            print(f"Enhance API Failed: {enhance_response.status_code} - {enhance_response.text}")
            message.reply_text("Sorry, the enhancement API is not working. Please try again later.")

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
