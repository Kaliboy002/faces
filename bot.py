import aiohttp
import asyncio
from pyrogram import Client, filters
from gradio_client import Client as GradioClient, file
import aiofiles

# Gradio Client setup
gradio_client = GradioClient("CharlieAmalet/Tools3ox_Background-Motion-Blur_Api")

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
async def upload_to_catbox(file_path):
    """Upload the file to Catbox and return the URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(file_path, "rb") as f:
                response = await session.post(
                    CATBOX_URL,
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": await f.read()},
                )
                response.raise_for_status()
                return (await response.text()).strip()
    except Exception as e:
        print(f"Failed to upload file to Catbox: {e}")
        return None

# Async function to process the image with Gradio API
async def process_image(image_url, distance_blur=200, amount_blur=1):
    """Process the image by applying motion blur and return the result filepath."""
    try:
        result = await gradio_client.async_predict(  # Use async_predict to handle async generators
            img=file(image_url),  # URL of the image to process
            distance_blur=distance_blur,
            amount_blur=amount_blur,
            api_name="/blur"
        )
        
        # If the result is a string (file path), return it
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
async def start(bot, message):
    await message.reply("Welcome! Send me a photo to apply motion blur.")

# Handle photo messages
@bot.on_message(filters.photo)
async def handle_photo(bot, message):
    chat_id = message.chat.id

    try:
        # Download the photo sent by the user
        file_id = message.photo.file_id
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        # Process the image via the Gradio API
        print(f"Processing image: {file_url}")
        processed_image_path = await process_image(file_url)

        if processed_image_path:
            # Upload the processed image to Catbox
            catbox_url = await upload_to_catbox(processed_image_path)

            if catbox_url:
                # Send the Catbox URL back to the user
                await message.reply(f"Here is your motion-blurred image: {catbox_url}")
            else:
                await message.reply("Failed to upload the image to Catbox.")
        else:
            await message.reply("Failed to process the image.")

    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")
        print(f"Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    bot.run()
