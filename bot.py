import os
import aiohttp
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient, handle_file
from PIL import Image

# Gradio Client setup for Hepzeka API
HEPZEKA_API = GradioClient("mukaist/finegrain-image-enhancer")

# ImgBB API URL and API Key for uploading images
IMGBB_API_URL = "https://api.imgbb.com/1/upload"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"  # Your ImgBB API key

# Telegram Bot Token
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"  # Replace with your Telegram bot token

# Your API ID and API Hash from Telegram
API_ID = "15787995"  # Replace with your API ID
API_HASH = "b34225445e8edd8349d8a9fe68f20369"  # Replace with your API Hash

# Create a Pyrogram client (Bot)
bot = Client("image_enhancer_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resize the image to a smaller size (max 1024px on the longest side)
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

# Async function to upload the image to ImgBB and return the URL
async def upload_to_imgbb(file_path: str) -> str:
    """Upload the file to ImgBB and return the URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with aiohttp.FormData() as form:
                form.add_field("key", IMGBB_API_KEY)
                with open(file_path, "rb") as file:
                    form.add_field("image", file)

                async with session.post(IMGBB_API_URL, data=form) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get("status") == 200:
                        return data["data"]["url"]
                    else:
                        logger.error(f"ImgBB API error: {data}")
                        return None
    except Exception as e:
        logger.error(f"Failed to upload file to ImgBB: {e}")
        return None

# Async function to process the image with Gradio API (Hepzeka Image Enhancer)
async def enhance_image(image_path: str, prompt: str = "", negative_prompt: str = "", upscale_factor: float = 2) -> str:
    """Enhance the image using the Hepzeka API and return the result filepath."""
    try:
        result = HEPZEKA_API.predict(
            input_image=handle_file(image_path),  # Path to the image file
            prompt=prompt,
            negative_prompt=negative_prompt,
            upscale_factor=upscale_factor,
            controlnet_scale=0.6,
            controlnet_decay=1,
            condition_scale=6,
            tile_width=112,
            tile_height=144,
            denoise_strength=0.35,
            num_inference_steps=12,  # Reduced inference steps for faster processing
            solver="DDIM",
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
        "Welcome! Send me a photo to enhance.\n\n"
        "You can customize the enhancement by sending:\n"
        "/enhance <prompt> <negative_prompt> <upscale_factor>\n\n"
        "Example: /enhance \"Brighten the image\" \"Reduce noise\" 2"
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

        # Default enhancement parameters
        prompt = ""
        negative_prompt = ""
        upscale_factor = 2

        # Check if the user provided custom parameters in the caption
        if message.caption and message.caption.startswith("/enhance"):
            try:
                _, prompt, negative_prompt, upscale_factor = message.caption.split(maxsplit=3)
                upscale_factor = float(upscale_factor)
            except Exception as e:
                logger.error(f"Failed to parse enhancement parameters: {e}")
                await message.reply("Invalid enhancement parameters. Using default values.")

        # Enhance the image via the Hepzeka API
        logger.info(f"Enhancing image: {resized_image_path}")
        enhanced_image_path = await enhance_image(resized_image_path, prompt, negative_prompt, upscale_factor)

        if enhanced_image_path:
            # Upload the enhanced image to ImgBB
            imgbb_url = await upload_to_imgbb(enhanced_image_path)
            if imgbb_url:
                # Send the ImgBB URL back to the user
                await message.reply_photo(
                    imgbb_url,
                    caption=f"✅ Here's your enhanced image!\n\n"
                            f"Prompt: {prompt}\n"
                            f"Negative Prompt: {negative_prompt}\n"
                            f"Upscale Factor: {upscale_factor}"
                )
            else:
                await message.reply("Failed to upload the image to ImgBB.")
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
