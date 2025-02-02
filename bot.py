import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# Replace with your credentials
API_ID = 15787995  # Get from https://my.telegram.org
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Get from https://my.telegram.org
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"  # Get from https://api.imgbb.com/

# Initialize Pyrogram client
app = Client("bg_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# API endpoint
BG_REMOVE_API = "https://for-free.serv00.net/ai-removebg.php?image="

def upload_to_imgbb(image_path):
    """Upload image to imgBB and return URL"""
    try:
        with open(image_path, "rb") as file:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                files={"image": file},
                data={"key": IMGBB_API_KEY}
            )
            if response.status_code == 200:
                return response.json()["data"]["url"]
            print(f"imgBB Upload Failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error uploading to imgBB: {e}")
        return None

def remove_background(image_url):
    """Call background removal API"""
    try:
        response = requests.get(f"{BG_REMOVE_API}{image_url}")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return data["results"][0]["image"]  # Return processed image URL
        print(f"BG Removal API Failed: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"Error in BG Removal API: {e}")
        return None

@app.on_message(filters.command("start"))
def start_handler(client: Client, message: Message):
    message.reply_text("🖼️ Send me a photo to remove its background!")

@app.on_message(filters.photo)
async def photo_handler(client: Client, message: Message):
    try:
        # Download the photo
        photo_path = await message.download()
        print(f"Downloaded photo: {photo_path}")

        # Upload to imgBB
        imgbb_url = upload_to_imgbb(photo_path)
        if not imgbb_url:
            await message.reply_text("❌ Failed to upload image. Please try again.")
            return

        print(f"Uploaded to imgBB: {imgbb_url}")

        # Process image
        processed_url = remove_background(imgbb_url)
        if not processed_url:
            await message.reply_text("❌ Background removal failed. Please try another image.")
            return

        print(f"Processed image URL: {processed_url}")

        # Send result
        await message.reply_photo(
            processed_url,
            caption="✅ Background removed successfully!"
        )

    except Exception as e:
        print(f"Error processing image: {e}")
        await message.reply_text("❌ An error occurred. Please try again.")

    finally:
        # Cleanup
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)

if __name__ == "__main__":
    print("Bot started...")
    app.run()
