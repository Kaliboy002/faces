import os
import logging
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient, handle_file

# Gradio Face Swap API Client
GRADIO_CLIENT = GradioClient("Kaliboy002/face-swapm")

# ImgBB API Details
IMGBB_API_URL = "https://api.imgbb.com/1/upload"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"

# Telegram Bot Credentials
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"

# Create Pyrogram Client (Bot)
bot = Client("face_swap_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to store user session data
user_sessions = {}

@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command."""
    user_sessions[message.chat.id] = {"step": "source"}
    await message.reply("👋 Send the **source image** (face to swap).")

@bot.on_message(filters.photo)
async def handle_photos(client: Client, message: Message):
    """Handles photo messages for face swapping."""
    chat_id = message.chat.id

    # Ensure user session exists
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"step": "source"}

    step = user_sessions[chat_id]["step"]
    file_path = await message.download()

    if step == "source":
        user_sessions[chat_id]["source"] = file_path
        user_sessions[chat_id]["step"] = "target"
        await message.reply("✅ Source image received!\nNow send the **target image** (where the face will be swapped).")

    elif step == "target":
        user_sessions[chat_id]["target"] = file_path
        user_sessions[chat_id]["step"] = "processing"
        await message.reply("⏳ Processing face swap... Please wait.")

        # Process face swap
        swapped_image = await process_face_swap(user_sessions[chat_id]["source"], file_path)

        if swapped_image:
            # Upload to ImgBB
            imgbb_url = await upload_to_imgbb(swapped_image)

            if imgbb_url:
                await message.reply_photo(imgbb_url, caption="🤩 Here is your swapped face image!")
            else:
                await message.reply("❌ Failed to upload image to ImgBB.")
        else:
            await message.reply("❌ Face swap failed. Please try again.")

        # Cleanup
        os.remove(user_sessions[chat_id]["source"])
        os.remove(file_path)
        if swapped_image:
            os.remove(swapped_image)

        del user_sessions[chat_id]

async def process_face_swap(source: str, target: str) -> str:
    """Processes face swap using Gradio API."""
    try:
        result = GRADIO_CLIENT.predict(
            source_file=handle_file(source),
            target_file=handle_file(target),
            doFaceEnhancer=False,
            api_name="/predict"
        )
        return result if isinstance(result, str) else None
    except Exception as e:
        logger.error(f"Face swap error: {e}")
        return None

async def upload_to_imgbb(file_path: str) -> str:
    """Uploads the processed image to ImgBB."""
    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("key", IMGBB_API_KEY)
            with open(file_path, "rb") as file:
                form.add_field("image", file)

            async with session.post(IMGBB_API_URL, data=form) as response:
                data = await response.json()
                return data["data"]["url"] if data.get("status") == 200 else None
    except Exception as e:
        logger.error(f"ImgBB upload error: {e}")
        return None

if __name__ == "__main__":
    logger.info("Starting Face Swap Bot...")
    bot.run()
