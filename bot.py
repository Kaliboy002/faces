import os
import requests
from pyrogram import Client, filters

# Replace these with your credentials
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"

bot = Client("image_enhancer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("📸 Send me an image, and I'll enhance its quality!")

@bot.on_message(filters.photo)
def enhance_image(client, message):
    msg = message.reply_text("🔄 Enhancing your image, please wait...")

    # Download the image
    file_path = client.download_media(message.photo.file_id)

    # Upload to tmpfiles.org
    with open(file_path, "rb") as file:
        upload_response = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": file})
    
    if upload_response.status_code == 200 and upload_response.json().get("data"):
        tmp_url = upload_response.json()["data"]["url"]
        
        # Send request to enhancement API
        api_url = f"https://ar-api-08uk.onrender.com/remini?url={tmp_url}"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 200:
                enhanced_url = data.get("result")
                message.reply_photo(enhanced_url, caption="✅ Here is your enhanced image!")
            else:
                message.reply_text("❌ Error enhancing the image.")
        else:
            message.reply_text("❌ API request failed.")
    else:
        message.reply_text("❌ Failed to upload image for processing.")

    msg.delete()
    os.remove(file_path)  # Clean up

bot.run()
