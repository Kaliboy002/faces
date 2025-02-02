import os
import aiohttp
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient

# Gradio Client for Face Swap
GRADIO_CLIENT = GradioClient("Kaliboy002/face-swapm")

# ImgBB API URL and Key
IMGBB_API_URL = "https://api.imgbb.com/1/upload"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"  # Replace with your ImgBB API key

# Telegram Bot Credentials
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"  # Replace with your Telegram bot token
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash

# Create a Pyrogram client
bot = Client("face_swap_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to track user progress
user_sessions = {}


async def upload_to_imgbb(file_path: str) -> str:
    """Upload an image to ImgBB and return the URL."""
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as file:
                data = aiohttp.FormData()
                data.add_field("key", IMGBB_API_KEY)
                data.add_field("image", file)

                async with session.post(IMGBB_API_URL, data=data) as response:
                    result = await response.json()
                    if result.get("status") == 200:
                        return result["data"]["url"]
                    else:
                        logger.error(f"ImgBB API error: {result}")
                        return None
    except Exception as e:
        logger.error(f"Failed to upload file to ImgBB: {e}")
        return None


async def swap_faces(source: str, target: str) -> str:
    """Perform face swap using Gradio API and return the processed image path."""
    try:
        result = GRADIO_CLIENT.predict(
            source_file=source,
            target_file=target,
            doFaceEnhancer=False,
            api_name="/predict"
        )
        if isinstance(result, str):
            return result
        else:
            logger.error(f"Unexpected API response: {result}")
            return None
    except Exception as e:
        logger.error(f"Error swapping faces: {e}")
        return None


@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command."""
    user_sessions[message.from_user.id] = {"step": "waiting_source"}
    await message.reply("👋 Send me the **source image** (the face you want to swap).")


@bot.on_message(filters.photo)
async def handle_photo(client: Client, message: Message):
    """Handles photo messages for face swap."""
    user_id = message.from_user.id

    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": "waiting_source"}

    step = user_sessions[user_id]["step"]

    file_path = await message.download()

    if step == "waiting_source":
        user_sessions[user_id]["source"] = file_path
        user_sessions[user_id]["step"] = "waiting_target"
        await message.reply("✅ Source image received! Now send the **target image** (the face you want to replace).")

    elif step == "waiting_target":
        user_sessions[user_id]["target"] = file_path
        await message.reply("⏳ Processing face swap... Please wait.")

        source_path = user_sessions[user_id]["source"]
        target_path = user_sessions[user_id]["target"]

        # Perform face swap
        swapped_image_path = await swap_faces(source_path, target_path)

        if swapped_image_path:
            # Upload result to ImgBB
            imgbb_url = await upload_to_imgbb(swapped_image_path)
            if imgbb_url:
                await message.reply_photo(imgbb_url, caption="✅ Face Swap Completed!")
            else:
                await message.reply("❌ Failed to upload swapped image.")
        else:
            await message.reply("❌ Face swap failed. Please try again.")

        # Cleanup
        os.remove(source_path)
        os.remove(target_path)
        user_sessions.pop(user_id, None)  # Reset user session

    else:
        await message.reply("Send the **source image** first.")


if __name__ == "__main__":
    logger.info("Starting Face Swap Bot...")
    bot.run()
