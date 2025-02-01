import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
from rembg import remove
import cv2
import numpy as np
from moviepy.editor import VideoFileClip
from io import BytesIO
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

# Initialize the Pyrogram client
app = Client("motion_blur_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper functions
def cv_to_pil(img):
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))

def pil_to_cv(img):
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)

def motion_blur(img, distance, amount):
    img = img.convert('RGBA')
    cv_img = pil_to_cv(img)
    kernel_motion_blur = np.zeros((distance, distance))
    kernel_motion_blur[int((distance-1)/2), :] = np.ones(distance)
    kernel_motion_blur = kernel_motion_blur / distance
    output = cv2.filter2D(cv_img, -1, kernel_motion_blur)
    blur_img = cv_to_pil(output).convert('RGBA')
    final_img = Image.blend(img, blur_img, amount)
    return final_img

def background_motion_blur(background, distance_blur, amount_blur, amount_subject):
    subject = remove(background)
    background_blur = motion_blur(background, distance_blur, amount_blur)
    subject_on_blur_background = background_blur.copy()
    subject_on_blur_background.paste(background, (0,0), subject)
    result = Image.blend(background_blur, subject_on_blur_background, amount_subject)
    return result

def process_image(image_path):
    img = Image.open(image_path)
    blurred_img = background_motion_blur(img, distance_blur=100, amount_blur=0.75, amount_subject=1.0)
    blurred_img.save("blurred_image.png")
    return "blurred_image.png"

def process_video(video_path):
    clip = VideoFileClip(video_path)
    blurred_clip = clip.fl_image(lambda frame: np.array(background_motion_blur(Image.fromarray(frame), 100, 0.75, 1.0)))
    blurred_clip.write_videofile("blurred_video.mp4", codec="libx264")
    return "blurred_video.mp4"

# Telegram bot handlers
@app.on_message(filters.photo | filters.video)
async def handle_media(client: Client, message: Message):
    try:
        await message.reply("Processing your media...")

        # Download the media
        media_path = await message.download()

        # Process the media
        if message.photo:
            output_path = process_image(media_path)
            await message.reply_photo(output_path)
        elif message.video:
            output_path = process_video(media_path)
            await message.reply_video(output_path)

        # Clean up
        os.remove(media_path)
        os.remove(output_path)

    except Exception as e:
        logger.error(f"Error processing media: {e}")
        await message.reply("An error occurred while processing your media.")

# Start the bot
if __name__ == "__main__":
    app.run()
