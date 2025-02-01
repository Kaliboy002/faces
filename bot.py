import os
import requests
from pyrogram import Client, filters

# Replace with your credentials
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"

# Catbox Upload Function
def upload_to_catbox(file_path):
    with open(file_path, "rb") as file:
        response = requests.post("https://catbox.moe/user/api.php", 
                                 data={"reqtype": "fileupload"}, 
                                 files={"fileToUpload": file})
    if response.status_code == 200 and response.text.startswith("https"):
        return response.text.strip()  # Return direct image link
    return None  # Return None if upload failed

bot = Client("image_enhancer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("📸 Send me an image, and I'll enhance its quality!")

@bot.on_message(filters.photo | filters.document)
def enhance_image(client, message):
    msg = message.reply_text("🔄 Enhancing your image, please wait...")

    # Download user's image
    file_path = client.download_media(message)

    # Upload original image to Catbox
    catbox_url = upload_to_catbox(file_path)
    if not catbox_url:
        message.reply_text("❌ Failed to upload image to Catbox. Try again!")
        return

    # Send request to enhancement API
    api_url = f"https://ar-api-08uk.onrender.com/remini?url={catbox_url}"
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == 200:
            enhanced_url = data.get("result")

            # 🔽 Download the enhanced image
            enhanced_image_path = "enhanced_image.jpg"
            img_data = requests.get(enhanced_url).content
            with open(enhanced_image_path, "wb") as img_file:
                img_file.write(img_data)

            # 📤 Upload the enhanced image to Catbox
            final_url = upload_to_catbox(enhanced_image_path)
            if final_url:
                message.reply_photo(final_url, caption="✅ Here is your enhanced image!")
                message.reply_text(f"🔗 **Permanent Link:** {final_url}", disable_web_page_preview=True)
            else:
                message.reply_text("✅ Here is your enhanced image (temporary):")
                message.reply_photo(enhanced_image_path)

            # Cleanup
            os.remove(enhanced_image_path)
        else:
            message.reply_text("❌ Error enhancing the image.")
    else:
        message.reply_text("❌ API request failed.")

    msg.delete()
    os.remove(file_path)  # Cleanup original file

bot.run()
