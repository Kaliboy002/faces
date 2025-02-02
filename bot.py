import os
import logging
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient, handle_file

# Gradio Client setup (Face Swap API)
GRADIO_CLIENT = GradioClient("Kaliboy002/face-swapm")

# Telegram Bot Credentials
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"
API_ID = "15787995"
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"

# Create a Pyrogram Client (Bot)
bot = Client("face_swap_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to store user session data
user_sessions = {}

@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command and starts the face swap process."""
    user_sessions[message.chat.id] = {"step": "source"}
    await message.reply("👋 Welcome! Send me the **source** image (the face you want to swap).")

@bot.on_message(filters.photo)
async def handle_photos(client: Client, message: Message):
    """Handles photo messages and processes them step by step."""
    chat_id = message.chat.id

    # Ensure user session exists
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"step": "source"}

    step = user_sessions[chat_id]["step"]
    file_path = await message.download()

    if step == "source":
        user_sessions[chat_id]["source"] = file_path
        user_sessions[chat_id]["step"] = "target"
        await message.reply("✅ Source image received!\nNow, send the **target** image (where you want to swap the face).")
    
    elif step == "target":
        user_sessions[chat_id]["target"] = file_path
        user_sessions[chat_id]["step"] = "processing"
        await message.reply("⏳ Processing face swap... Please wait.")

        # Process face swap
        swapped_image = await process_face_swap(user_sessions[chat_id]["source"], file_path)

        if swapped_image:
            await message.reply_photo(swapped_image, caption="🤩 Here is your swapped face image!")
        else:
            await message.reply("❌ Failed to swap faces. Please try again.")

        # Cleanup and reset user session
        os.remove(user_sessions[chat_id]["source"])
        os.remove(file_path)
        if swapped_image:
            os.remove(swapped_image)

        del user_sessions[chat_id]

async def process_face_swap(source: str, target: str) -> str:
    """Processes face swap using Gradio API and returns the output file path."""
    try:
        result = GRADIO_CLIENT.predict(
            source_file=handle_file(source),
            target_file=handle_file(target),
            doFaceEnhancer=False,  # Keeping it lightweight
            api_name="/predict"
        )
        return result if isinstance(result, str) else None
    except Exception as e:
        logger.error(f"Face swap error: {e}")
        return None

if __name__ == "__main__":
    logger.info("Starting Face Swap Bot...")
    bot.run()
