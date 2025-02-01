import os
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient, file
import aiofiles

# Gradio Client setup
GRADIO_CLIENT = GradioClient("CharlieAmalet/Tools3ox_Background-Motion-Blur_Api")

# Catbox API URL
CATBOX_URL = "https://catbox.moe/user/api.php"

# Telegram Bot Token
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"  # Replace with your Telegram bot token

# Your API ID and API Hash from Telegram
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash

# Create a Pyrogram client (Bot)
bot = Client("motion_blur_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Async function to upload to Catbox
async def upload_to_catbox(file_path: str) -> str:
    """Upload the file to Catbox and return the URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("reqtype", "fileupload")
                data.add_field("fileToUpload", await f.read(), filename=os.path.basename(file_path))

                async with session.post(CATBOX_URL, data=data) as response:
                    response.raise_for_status()
                    return (await response.text()).strip()
    except Exception as e:
        print(f"Failed to upload file to Catbox: {e}")
        return None

# Async function to process the image with Gradio API
async def process_image(image_path: str, distance_blur: int = 200, amount_blur: float = 1) -> str:
    """Process the image by applying motion blur and return the result filepath."""
    try:
        # Use the Gradio API to process the image
        result = GRADIO_CLIENT.predict(
            img=file(image_path),  # Path to the image file
            distance_blur=distance_blur,
            amount_blur=amount_blur,
            api_name="/blur"
        )

        # The result is a filepath to the processed image
        if isinstance(result, str):
            return result
        else:
            print(f"Unexpected result format: {result}")
            return None
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

# Handle the /start command
@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command."""
    await message.reply("Welcome! Send me a photo to apply motion blur.")

# Handle photo messages
@bot.on_message(filters.photo)
async def handle_photo(client: Client, message: Message):
    """Handles photo messages and processes them."""
    try:
        # Download the photo sent by the user
        file_id = message.photo.file_id
        file_path = await message.download()

        # Process the image via the Gradio API
        print(f"Processing image: {file_path}")
        processed_image_path = await process_image(file_path)

        if processed_image_path:
            # Upload the processed image to Catbox
            catbox_url = await upload_to_catbox(processed_image_path)

            if catbox_url:
                # Send the Catbox URL back to the user
                await message.reply_photo(catbox_url, caption="Here is your motion-blurred image!")
            else:
                await message.reply("Failed to upload the image to Catbox.")
        else:
            await message.reply("Failed to process the image.")

        # Clean up downloaded and processed files
        os.remove(file_path)
        if processed_image_path:
            os.remove(processed_image_path)
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")
        print(f"Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    print("Starting Motion Blur Bot...")
    bot.run()
