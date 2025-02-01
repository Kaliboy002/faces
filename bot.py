import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram API credentials
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Motion Blur API URL
MOTION_BLUR_API_URL = "https://gyufyjk-motion-blur.hf.space/--replicas/696du/"

# Initialize the Pyrogram client
app = Client("motion_blur_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to upload image to Catbox
def upload_to_catbox(image_path):
    with open(image_path, "rb") as file:
        response = requests.post(
            "https://catbox.moe/user/api.php",
            files={"fileToUpload": file},
            data={"reqtype": "fileupload"}
        )
    if response.status_code == 200:
        return response.text.strip()
    else:
        raise Exception("Failed to upload image to Catbox")

# Telegram bot handler
@app.on_message(filters.photo)
async def handle_photo(client: Client, message: Message):
    try:
        await message.reply("Processing your photo...")

        # Download the photo
        photo_path = await message.download()

        # Process the photo using the Motion Blur API
        gradio_client = GradioClient(MOTION_BLUR_API_URL)
        result = gradio_client.predict(
            photo_path,  # Image path
            100,        # Blur Distance
            0.75,       # Blur Amount
            1.0,        # Subject Amount
            api_name="/predict"
        )

        # Upload the processed image to Catbox
        catbox_url = upload_to_catbox(result)

        # Send the Catbox URL to the user
        await message.reply_photo(
            catbox_url,
            caption=f"Motion Blur by Tony Assi\n\nCatbox URL: {catbox_url}"
        )

        # Clean up
        os.remove(photo_path)
        os.remove(result)

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.reply("An error occurred while processing your photo.")

# Start the bot
if __name__ == "__main__":
    app.run()
