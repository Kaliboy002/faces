import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient, handle_file
from PIL import Image

# Gradio Client setup for Hepzeka API
HEPZEKA_API = GradioClient("mukaist/finegrain-image-enhancer")

# Telegram Bot Token
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"  # Replace with your Telegram bot token

# Your API ID and API Hash from Telegram
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash

# Create a Pyrogram client (Bot)
bot = Client("image_enhancer_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resize the image to a manageable size (max 1024px on the longest side)
def resize_image(image_path: str, max_size: int = 1024):
    """Resize the image to a manageable size for faster processing."""
    with Image.open(image_path) as img:
        width, height = img.size
        if width > height:
            ratio = max_size / width
            new_width = max_size
            new_height = int(height * ratio)
        else:
            ratio = max_size / height
            new_width = int(width * ratio)
            new_height = max_size
        img = img.resize((new_width, new_height), Image.LANCZOS)
        resized_path = image_path.replace(".jpg", "_resized.jpg")
        img.save(resized_path)
        return resized_path

# Async function to process the image with Gradio API (Hepzeka Image Enhancer)
async def enhance_image(image_path: str) -> str:
    """Enhance the image using the Hepzeka API and return the result filepath."""
    try:
        result = HEPZEKA_API.predict(
            input_image=handle_file(image_path),  # Path to the image file
            prompt="",  # Default empty prompt
            negative_prompt="",  # Default empty negative prompt
            upscale_factor=2,  # Default upscale factor
            controlnet_scale=0.6,  # Default ControlNet scale
            controlnet_decay=1,  # Default ControlNet decay
            condition_scale=6,  # Default condition scale
            tile_width=112,  # Default tile width
            tile_height=144,  # Default tile height
            denoise_strength=0.35,  # Default denoise strength
            num_inference_steps=12,  # Default inference steps
            solver="DDIM",  # Default solver
            api_name="/process"
        )

        # The result should return the processed image file path
        if isinstance(result, tuple) and result[1]:
            return result[1]
        else:
            logger.error(f"Unexpected result format: {result}")
            return None
    except Exception as e:
        logger.error(f"Error enhancing image: {e}")
        return None

# Handle the /start command
@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command."""
    await message.reply(
        "Welcome! Send me a photo to enhance. I will automatically process it using default settings."
    )

# Handle photo messages
@bot.on_message(filters.photo)
async def handle_photo(client: Client, message: Message):
    """Handles photo messages and processes them."""
    try:
        # Download the photo sent by the user
        file_path = await message.download()

        # Resize the image to a smaller size
        resized_image_path = resize_image(file_path)

        # Enhance the image via the Hepzeka API
        logger.info(f"Enhancing image: {resized_image_path}")
        enhanced_image_path = await enhance_image(resized_image_path)

        if enhanced_image_path:
            # Send the enhanced image back to the user
            await message.reply_photo(
                enhanced_image_path,
                caption="✅ Here's your enhanced image!"
            )
        else:
            await message.reply("Failed to enhance the image.")

        # Clean up downloaded and processed files
        os.remove(file_path)
        if resized_image_path != file_path:
            os.remove(resized_image_path)
        if enhanced_image_path:
            os.remove(enhanced_image_path)
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")
        logger.error(f"Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    logger.info("Starting Image Enhancer Bot...")
    bot.run()
