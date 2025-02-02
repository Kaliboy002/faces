import os
import requests
from pyrogram import Client, filters

# Replace with your credentials
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"

# Catbox Upload Function
def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as file:
            response = requests.post("https://catbox.moe/user/api.php", 
                                     data={"reqtype": "fileupload"}, 
                                     files={"fileToUpload": file})
        
        if response.status_code == 200 and response.text.startswith("https"):
            return response.text.strip()  # Return direct image link
        else:
            print(f"Error uploading to Catbox: {response.text}")
            return None  # Return None if upload failed
    except requests.RequestException as e:
        print(f"Request failed during Catbox upload: {e}")
        return None

bot = Client("remove_bg_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("📸 Send me an image, and I'll remove its background!")

@bot.on_message(filters.photo | filters.document)
def remove_background(client, message):
    msg = message.reply_text("🔄 Removing background, please wait...")

    try:
        # Download user's image
        file_path = client.download_media(message)
        
        if not file_path:
            message.reply_text("❌ Failed to download image. Please try again!")
            return
        
        # Upload original image to Catbox
        catbox_url = upload_to_catbox(file_path)
        if not catbox_url:
            message.reply_text("❌ Failed to upload image to Catbox. Try again!")
            return

        # Send request to the new API to process the image
        api_url = f"https://api.nyxs.pw/tools/hd?url={catbox_url}"
        response = requests.get(api_url)

        if response.status_code == 200:
            data = response.json()

            if data.get("status") == True:
                # Extract the result URL for the processed image
                processed_image_url = data["result"]

                # Send the processed image URL directly to the user
                message.reply_photo(processed_image_url, caption="✅ Here is your background-removed image!")

                # Cleanup
                os.remove(file_path)  # Clean up original file
            else:
                message.reply_text("❌ Error processing the image.")
        else:
            message.reply_text("❌ API request failed.")

    except Exception as e:
        print(f"Error during processing: {e}")
        message.reply_text("❌ An unexpected error occurred. Please try again.")

    finally:
        msg.delete()

bot.run()
