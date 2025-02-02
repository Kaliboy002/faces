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

# Function to upload image to imgbb (or any other service)
def upload_to_imgbb(image_url):
    imgbb_api_key = "b34225445e8edd8349d8a9fe68f20369"  # Replace with your imgbb API key
    upload_url = "https://api.imgbb.com/1/upload"
    params = {
        "key": imgbb_api_key,
        "image": image_url,
    }
    response = requests.post(upload_url, params=params)
    if response.status_code == 200:
        return response.json()["data"]["url"]
    return None

# Start command handler
@app.on_message(filters.command("start"))
def start(client: Client, message: Message):
    message.reply_text("Hi! Send me a photo, and I'll enhance it for you.")

# Photo handler
@app.on_message(filters.photo)
def enhance_photo(client: Client, message: Message):
    # Download the photo
    photo_path = message.download()
    
    # Upload the photo to a temporary URL (using imgbb)
    enhanced_url = None
    with open(photo_path, "rb") as photo_file:
        imgbb_url = upload_to_imgbb(photo_file)
        if imgbb_url:
            # Enhance the photo using the API
            response = requests.get(f"{ENHANCE_API}{imgbb_url}")
            if response.status_code == 200:
                enhanced_url = response.json()["result"]
    
    # Send the enhanced photo back to the user
    if enhanced_url:
        message.reply_photo(enhanced_url, caption="Here's your enhanced photo!")
    else:
        message.reply_text("Sorry, something went wrong while processing your photo.")
    
    # Clean up the downloaded file
    os.remove(photo_path)

# Run the bot
if __name__ == "__main__":
    print("Bot started...")
    app.run()
