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

bot = Client("remove_bg_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("📸 Send me an image, and I'll remove its background!")

@bot.on_message(filters.photo | filters.document)
def remove_background(client, message):
    msg = message.reply_text("🔄 Removing background, please wait...")

    # Download user's image
    file_path = client.download_media(message)

    # Upload original image to Catbox
    catbox_url = upload_to_catbox(file_path)
    if not catbox_url:
        message.reply_text("❌ Failed to upload image to Catbox. Try again!")
        return

    # Send request to remove background API
    api_url = f"https://ar-api-08uk.onrender.com/remove?bg={catbox_url}"
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            bg_removed_url = data["results"][0]["image"]

            # 🔽 Download the background-removed image
            output_image_path = "bg_removed.png"
            img_data = requests.get(bg_removed_url).content
            with open(output_image_path, "wb") as img_file:
                img_file.write(img_data)

            # 📤 Upload the processed image to Catbox
            final_url = upload_to_catbox(output_image_path)
            if final_url:
                message.reply_photo(final_url, caption="✅ Here is your background-removed image!")
                message.reply_text(f"🔗 **Permanent Link:** {final_url}", disable_web_page_preview=True)
            else:
                message.reply_text("✅ Here is your background-removed image (temporary):")
                message.reply_photo(output_image_path)

            # Cleanup
            os.remove(output_image_path)
        else:
            message.reply_text("❌ Error processing the image.")
    else:
        message.reply_text("❌ API request failed.")

    msg.delete()
    os.remove(file_path)  # Cleanup original file

bot.run()
