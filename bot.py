import os
import httpx
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Bot credentials
API_ID = 15787995  
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"

# API endpoints
BG_REMOVE_APIS = [
    "https://for-free.serv00.net/ai-removebg.php?image=",
    "https://ar-api-08uk.onrender.com/remove?bg="
]
ENHANCE_APIS = [
    "https://ar-api-08uk.onrender.com/remini?url=",
    "https://api.nyxs.pw/tools/hd?url="
]

# Fixed image URLs
BG_REMOVE_IMAGE = "https://i.imghippo.com/files/eNXe4934iU.jpg"
ENHANCE_IMAGE = "https://files.catbox.moe/utlaxp.jpg"

# Initialize Pyrogram bot
app = Client("image_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store user selections
user_selections = {}

# Upload image to imgBB
async def upload_to_imgbb(image_path):
    try:
        with open(image_path, "rb") as file:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.imgbb.com/1/upload",
                    files={"image": file},
                    data={"key": IMGBB_API_KEY},
                    timeout=10
                )
        if response.status_code == 200:
            return response.json()["data"]["url"]
        print(f"imgBB Upload Failed: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"Error uploading to imgBB: {e}")
        return None

# Process image using multiple APIs
async def process_image(image_url, api_list):
    async with httpx.AsyncClient() as client:
        for api_url in api_list:
            try:
                response = await client.get(f"{api_url}{image_url}", timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success" or data.get("status") == 200:
                        return data["results"][0]["image"] if "results" in data else data["result"]
                print(f"API Failed: {api_url} - {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error in API {api_url}: {e}")
    return None

# Send selection buttons
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Remove Background", callback_data="remove_bg")],
        [InlineKeyboardButton("✨ Enhance Photo", callback_data="enhance_photo")]
    ])

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user_selections[message.from_user.id] = None  # Reset selection
    await message.reply_text(
        "Welcome! Choose an option:",
        reply_markup=get_main_buttons()
    )

@app.on_callback_query()
async def button_handler(client: Client, callback_query):
    user_choice = callback_query.data
    user_selections[callback_query.from_user.id] = user_choice

    image_url = BG_REMOVE_IMAGE if user_choice == "remove_bg" else ENHANCE_IMAGE
    description = "Send me a photo to remove its background!" if user_choice == "remove_bg" else "Send me a photo to enhance it!"

    await callback_query.message.edit_text(
        description,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
    )
    await callback_query.message.reply_photo(image_url)

@app.on_callback_query(filters.regex("back"))
async def back_handler(client: Client, callback_query):
    user_selections[callback_query.from_user.id] = None  # Reset selection
    await callback_query.message.edit_text(
        "Welcome back! Choose an option:",
        reply_markup=get_main_buttons()
    )

@app.on_message(filters.photo)
async def photo_handler(client: Client, message: Message):
    user_choice = user_selections.get(message.from_user.id)
    if not user_choice:
        await message.reply_text("Please select an option first.", reply_markup=get_main_buttons())
        return

    api_list = ENHANCE_APIS if user_choice == "enhance_photo" else BG_REMOVE_APIS

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_path = temp_file.name

    try:
        # Download the photo
        await message.download(temp_path)
        print(f"Downloaded: {temp_path}")

        # Upload to imgBB
        imgbb_url = await upload_to_imgbb(temp_path)
        if not imgbb_url:
            await message.reply_text("❌ Failed to upload image. Please try again.")
            return

        print(f"Uploaded to imgBB: {imgbb_url}")

        # Process image
        processed_url = await process_image(imgbb_url, api_list)
        if not processed_url:
            await message.reply_text("❌ Processing failed. Try another image.")
            return

        print(f"Processed image URL: {processed_url}")

        # Send processed image
        await message.reply_photo(processed_url, caption="✅ Done!")

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("❌ An error occurred. Try again.")

    finally:
        os.remove(temp_path)  # Cleanup temp file

if __name__ == "__main__":
    print("Bot started...")
    app.run()
