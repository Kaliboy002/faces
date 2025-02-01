import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from gradio_client import Client as GradioClient

# Initialize the Telegram bot
app = Client("motion_blur_bot", bot_token="7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y")

# Initialize the Gradio client for the Motion Blur API
gradio_client = GradioClient("https://gyufyjk-motion-blur.hf.space/--replicas/696du/")

# Function to upload image to Catbox
def upload_to_catbox(image_path):
    url = "https://catbox.moe/user/api.php"
    files = {'fileToUpload': open(image_path, 'rb')}
    data = {'reqtype': 'fileupload'}
    response = requests.post(url, files=files, data=data)
    return response.text

# Start command handler
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text("Please send me a photo to apply motion blur!")

# Photo message handler
@app.on_message(filters.photo)
async def process_photo(client: Client, message: Message):
    # Download the photo
    photo_path = await message.download()

    # Process the photo using the Gradio API
    result = gradio_client.predict(
        photo_path,  # Image path
        100,         # Blur Distance
        0.75,        # Blur Amount
        1,           # Subject Amount
        api_name="/predict"
    )

    # Upload the processed image to Catbox
    catbox_url = upload_to_catbox(result)

    # Send the processed image back to the user
    await message.reply_photo(catbox_url, caption="Here is your processed image!")

    # Clean up downloaded files
    os.remove(photo_path)
    os.remove(result)

# Run the bot
app.run()
