import os
import aiohttp
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient

# Gradio Client setup
GRADIO_CLIENT = GradioClient("AmanDev/motion-blur")

# ImgBB API URL and API Key
IMGBB_API_URL = "https://api.imgbb.com/1/upload"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"  # Your ImgBB API key

# Telegram Bot Token
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"  # Replace with your Telegram bot token

# Your API ID and API Hash from Telegram
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash

# Create a Pyrogram client (Bot)
bot = Client("motion_blur_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Async function to upload to ImgBB
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

# Async function to process the image with Gradio API
async def process_image(image_path: str, distance_blur: int = 100, amount_blur: float = 0.75, amount_subject: float = 1) -> str:
    """Process the image by applying motion blur and return the result filepath."""
    try:
        # Use the Gradio API to process the image
        result = GRADIO_CLIENT.predict(
            img=image_path,  # Path to the image file
            distance_blur=distance_blur,
            amount_blur=amount_blur,
            amount_subject=amount_subject,
            api_name="/predict"
        )

        # The result is a filepath to the processed image
        if isinstance(result, str):
            return result
        else:
            logger.error(f"Unexpected result format: {result}")
            return None
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return None

# Handle the /start command
@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command."""
    await message.reply(
        "Welcome! Send me a photo to apply motion blur.\n\n"
        "You can customize the blur effect by sending:\n"
        "/blur <distance> <amount> <subject>\n\n"
        "Example: /blur 100 0.75 1"
    )

# Handle photo messages
@bot.on_message(filters.photo)
async def handle_photo(client: Client, message: Message):
    """Handles photo messages and processes them."""
    try:
        # Download the photo sent by the user
        file_path = await message.download()

        # Default blur parameters
        distance_blur = 100
        amount_blur = 0.75
        amount_subject = 1

        # Check if the user provided custom parameters in the caption
        if message.caption and message.caption.startswith("/blur"):
            try:
                _, distance, amount, subject = message.caption.split()
                distance_blur = float(distance)
                amount_blur = float(amount)
                amount_subject = float(subject)
            except Exception as e:
                logger.error(f"Failed to parse blur parameters: {e}")
                await message.reply("Invalid blur parameters. Using default values.")

        # Process the image via the Gradio API
        logger.info(f"Processing image: {file_path}")
        processed_image_path = await process_image(file_path, distance_blur, amount_blur, amount_subject)

        if processed_image_path:
            # Upload the processed image to ImgBB
            imgbb_url = await upload_to_imgbb(processed_image_path)
            if imgbb_url:
                # Send the ImgBB URL back to the user
                await message.reply_photo(
                    imgbb_url,
                    caption=f"✅ Here's your motion-blurred image!\n\n"
                            f"Blur Distance: {distance_blur}\n"
                            f"Blur Amount: {amount_blur}\n"
                            f"Subject Amount: {amount_subject}"
                )
            else:
                await message.reply("Failed to upload the image to ImgBB.")
        else:
            await message.reply("Failed to process the image.")

        # Clean up downloaded and processed files
        os.remove(file_path)
        if processed_image_path:
            os.remove(processed_image_path)
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")
        logger.error(f"Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    logger.info("Starting Motion Blur Bot...")
    bot.run()
