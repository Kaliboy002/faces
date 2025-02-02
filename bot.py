import os
import httpx
import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from gradio_client import Client as GradioClient, file

# Bot credentials
API_ID = int(os.getenv("API_ID", "15787995"))
API_HASH = os.getenv("API_HASH", "e51a3154d2e0c45e5ed70251d68382de")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7844051995:AAHOprIiU0G8ZqBuw6o0zBzcIm-B-74ovK8")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "b34225445e8edd8349d8a9fe68f20369")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "7046488481"))

# Face swap API clients
FACE_SWAP_APIS = [
    "Kaliboy0012/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro"
]
current_client_index = 0

# API endpoints for other features
BG_REMOVE_APIS = [
    "https://for-free.serv00.net/ai-removebg.php?image=",
    "https://ar-api-08uk.onrender.com/remove?bg="
]
ENHANCE_APIS = [
    "https://ar-api-08uk.onrender.com/remini?url=",
    "https://api.nyxs.pw/tools/hd?url="
]

# Initialize Pyrogram bot
app = Client("image_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User data storage
user_data = {}
executor = ThreadPoolExecutor(max_workers=4)

def get_face_swap_client():
    """Return the current Face Swap API client."""
    global current_client_index
    return GradioClient(FACE_SWAP_APIS[current_client_index])

def switch_face_swap_client():
    """Switch to the next API client if one fails."""
    global current_client_index
    current_client_index = (current_client_index + 1) % len(FACE_SWAP_APIS)

def get_main_buttons():
    """Return the main menu buttons."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Remove Background", callback_data="remove_bg")],
        [InlineKeyboardButton("✨ Enhance Photo", callback_data="enhance_photo")],
        [InlineKeyboardButton("😎 Face Swap", callback_data="face_swap")]
    ])

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    """Start command handler."""
    user_data[message.from_user.id] = None  # Reset selection
    await message.reply_text("Welcome! Choose an option:", reply_markup=get_main_buttons())

@app.on_callback_query()
async def button_handler(client: Client, callback_query):
    """Handle button selections."""
    user_choice = callback_query.data
    user_data[callback_query.from_user.id] = {"choice": user_choice}

    await callback_query.message.delete()

    if user_choice == "remove_bg":
        await callback_query.message.reply_text("📷 Send a photo to remove its background!")
    elif user_choice == "enhance_photo":
        await callback_query.message.reply_text("✨ Send a photo to enhance it!")
    elif user_choice == "face_swap":
        user_data[callback_query.from_user.id]["step"] = "awaiting_source"
        await callback_query.message.reply_text("😎 Send the **source image** (face to swap).")

@app.on_message(filters.photo)
async def photo_handler(client: Client, message: Message):
    """Handle received photos."""
    user_choice = user_data.get(message.from_user.id)
    
    if not user_choice:
        await message.reply_text("Please select an option first.", reply_markup=get_main_buttons())
        return

    choice = user_choice.get("choice")

    if choice == "face_swap":
        await handle_face_swap(client, message)
    else:
        await process_image_feature(client, message, choice)

async def handle_face_swap(client: Client, message: Message):
    """Handles the Face Swap feature."""
    chat_id = message.chat.id
    if chat_id not in user_data:
        await client.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step")

    try:
        if step == "awaiting_source":
            file_id = message.photo.file_id
            source_path = f"{chat_id}_source.jpg"
            user_data[chat_id]["source_image"] = await download_telegram_photo(client, file_id, source_path)
            user_data[chat_id]["step"] = "awaiting_target"
            await client.send_message(chat_id, "Now send the **target image**.")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                await client.send_message(chat_id, "Source image is missing. Restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = message.photo.file_id
            target_path = f"{chat_id}_target.jpg"
            user_data[chat_id]["target_image"] = await download_telegram_photo(client, file_id, target_path)
            await client.send_message(chat_id, "Processing, please wait...")

            while True:
                try:
                    client_api = get_face_swap_client()
                    result = await asyncio.to_thread(client_api.predict,
                                                     source_file=file(user_data[chat_id]["source_image"]),
                                                     target_file=file(user_data[chat_id]["target_image"]),
                                                     doFaceEnhancer=True,
                                                     api_name="/predict")

                    # Upload to ImgBB
                    swapped_url = await upload_to_imgbb(result)
                    if swapped_url:
                        await client.send_photo(chat_id, photo=swapped_url, caption="✅ Face Swapped Successfully!")
                    else:
                        await client.send_message(chat_id, "❌ Failed to upload swapped image.")
                    break

                except Exception as e:
                    if "No such file" in str(e) or "Failed to download" in str(e):
                        await client.send_message(chat_id, "❌ Error processing images. Please try again.")
                        reset_user_data(chat_id)
                        return
                    switch_face_swap_client()
            
            reset_user_data(chat_id)

    except Exception as e:
        await client.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)

async def process_image_feature(client: Client, message: Message, choice):
    """Handles background removal and enhancement."""
    api_list = ENHANCE_APIS if choice == "enhance_photo" else BG_REMOVE_APIS
    temp_path = await download_telegram_photo(client, message.photo.file_id)

    try:
        imgbb_url = await upload_to_imgbb(temp_path)
        processed_url = await process_image(imgbb_url, api_list)

        if processed_url:
            await message.reply_photo(processed_url, caption="✅ Done!")
        else:
            await message.reply_text("❌ Processing failed. Try another image.")

    finally:
        os.remove(temp_path)  # Cleanup

async def download_telegram_photo(client: Client, file_id, save_as=None):
    """Download a photo from Telegram."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_path = save_as or temp_file.name
    await client.download_media(file_id, temp_path)
    return temp_path

async def upload_to_imgbb(image_path):
    """Upload image to ImgBB."""
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
        return None
    except:
        return None

async def process_image(image_url, api_list):
    """Process image through API."""
    async with httpx.AsyncClient() as client:
        for api_url in api_list:
            try:
                response = await client.get(f"{api_url}{image_url}", timeout=15)
                if response.status_code == 200:
                    return response.json().get("result") or response.json().get("results")[0]["image"]
            except:
                continue
    return None

def reset_user_data(chat_id):
    """Reset user data."""
    user_data.pop(chat_id, None)

if __name__ == "__main__":
    print("Bot started...")
    app.run()
