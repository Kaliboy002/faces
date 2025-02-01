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

# Initialize Gradio client for Motion Blur API
GRADIO_CLIENT = GradioClient("https://gyufyjk-motion-blur.hf.space/--replicas/696du/")

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
        "👋 Hello! Send me a photo, and I'll apply motion blur to the background while keeping the subject clear.\n\n"
        "Use /blur <distance> <amount> <subject> to customize the blur effect.\n\n"
        "Example: `/blur 100 0.75 1`"
    )

# Blur command handler
@app.on_message(filters.command("blur"))
async def blur_command(client: Client, message: Message):
    """Handles the /blur command to set custom blur parameters."""
    try:
        # Extract parameters from the command
        _, distance, amount, subject = message.text.split()
        distance = float(distance)
        amount = float(amount)
        subject = float(subject)

        # Validate parameters
        if not (0 <= distance <= 500 and 0 <= amount <= 1 and 0 <= subject <= 1):
            await message.reply_text("Invalid parameters. Ensure:\n"
                                    "- Blur Distance: 0 to 500\n"
                                    "- Blur Amount: 0.0 to 1.0\n"
                                    "- Subject Amount: 0.0 to 1.0")
            return

        # Ask for a photo
        await message.reply_text("Now send me a photo to process with these settings!")
    except Exception as e:
        await message.reply_text("Invalid command format. Use:\n"
                                "`/blur <distance> <amount> <subject>`\n\n"
                                "Example: `/blur 100 0.75 1`")

# Photo message handler
@app.on_message(filters.photo)
async def process_photo(client: Client, message: Message):
    """Processes the photo and applies motion blur."""
    try:
        # Download the photo
        photo_path = await message.download()

        # Default blur parameters
        blur_distance = 100
        blur_amount = 0.75
        subject_amount = 1

        # Check if the user provided custom parameters
        if message.caption and message.caption.startswith("/blur"):
            try:
                _, distance, amount, subject = message.caption.split()
                blur_distance = float(distance)
                blur_amount = float(amount)
                subject_amount = float(subject)
            except Exception as e:
                logger.warning(f"Failed to parse blur parameters: {e}")

        # Process the photo using the Gradio API
        result = GRADIO_CLIENT.predict(
            photo_path,          # Image path
            blur_distance,       # Blur Distance
            blur_amount,         # Blur Amount
            subject_amount,      # Subject Amount
            api_name="/predict"
        )

        # Upload the processed image to Catbox
        catbox_url = upload_to_catbox(result)
        if not catbox_url:
            await message.reply_text("Failed to upload the processed image. Please try again.")
            return

        # Send the processed image back to the user
        await message.reply_photo(
            catbox_url,
            caption=f"✅ Here's your processed image!\n\n"
                    f"Blur Distance: {blur_distance}\n"
                    f"Blur Amount: {blur_amount}\n"
                    f"Subject Amount: {subject_amount}"
        )

        # Clean up downloaded files
        os.remove(photo_path)
        os.remove(result)
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.reply_text("An error occurred while processing your photo. Please try again.")

# Run the bot
if __name__ == "__main__":
    logger.info("Starting Motion Blur Bot...")
    app.run()
