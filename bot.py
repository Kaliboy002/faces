import os
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pyrogram client
app = Client(
    "motion_blur_bot",
    api_id=os.getenv("API_ID"),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Initialize Gradio client for Motion Blur API (Hugging Face Space)
GRADIO_CLIENT = GradioClient("CharlieAmalet/Tools3ox_Background-Motion-Blur_Api")

# Catbox API URL
CATBOX_URL = "https://catbox.moe/user/api.php"

# Function to upload image to Catbox
def upload_to_catbox(image_path: str) -> str:
    """Uploads an image to Catbox and returns the URL."""
    try:
        with open(image_path, "rb") as file:
            files = {'fileToUpload': file}
            data = {'reqtype': 'fileupload'}
            response = requests.post(CATBOX_URL, files=files, data=data)
            response.raise_for_status()
            return response.text.strip()
    except Exception as e:
        logger.error(f"Failed to upload to Catbox: {e}")
        return None

# Start command handler
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command."""
    await message.reply_text(
        "👋 Hello! Please send me a photo to apply motion blur to the background while keeping the subject clear.\n\n"
        "I will process your photo and send it back to you after applying the effect!"
    )

# Photo message handler
@app.on_message(filters.photo)
async def process_photo(client: Client, message: Message):
    """Processes the photo and applies motion blur."""
    try:
        # Download the photo
        photo_path = await message.download()

        # Default blur parameters
        blur_distance = 200
        blur_amount = 1

        # Process the photo using the Gradio API
        result = GRADIO_CLIENT.predict(
            img=photo_path,           # Image path
            distance_blur=blur_distance, # Blur Distance
            amount_blur=blur_amount,    # Blur Amount
            api_name="/blur"
        )

        # The result is the path of the processed image
        result_image_path = result[0]

        # Upload the processed image to Catbox
        catbox_url = upload_to_catbox(result_image_path)
        if not catbox_url:
            await message.reply_text("Failed to upload the processed image. Please try again.")
            return

        # Send the processed image back to the user
        await message.reply_photo(
            catbox_url,
            caption="✅ Here's your processed image with motion blur applied to the background!"
        )

        # Clean up downloaded files
        os.remove(photo_path)
        os.remove(result_image_path)
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.reply_text("An error occurred while processing your photo. Please try again.")

# Run the bot
if __name__ == "__main__":
    logger.info("Starting Motion Blur Bot...")
    app.run()
