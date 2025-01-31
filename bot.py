import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
import ffmpeg
import asyncio

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Environment Variables
API_ID = os.getenv("15787995")  # Get from https://my.telegram.org
API_HASH = os.getenv("e51a3154d2e0c45e5ed70251d68382de")  # Get from https://my.telegram.org
BOT_TOKEN = os.getenv("7844051995:AAHTkN2eJswu-CAfe74amMUGok_jaMK0hXQ")  # Get from BotFather

# Initialize Pyrogram Client
app = Client("video_compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Compression Settings
COMPRESSED_VIDEO_DIR = "compressed_videos"
os.makedirs(COMPRESSED_VIDEO_DIR, exist_ok=True)

def compress_video(input_path, output_path, crf=28, preset="medium"):
    """Compress video using ffmpeg."""
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, vcodec="libx264", crf=crf, preset=preset)
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        return True
    except ffmpeg.Error as e:
        logging.error(f"FFmpeg error: {e.stderr.decode()}")
        return False

async def send_progress(message: Message, progress: float):
    """Send progress updates to the user."""
    await message.edit_text(f"Compressing... {int(progress * 100)}%")

@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
    """Handle incoming video files."""
    try:
        # Download the video
        await message.reply("📥 Downloading video...")
        video_path = await message.download()

        # Compress the video
        await message.reply("🔧 Compressing video...")
        compressed_video_path = os.path.join(COMPRESSED_VIDEO_DIR, f"compressed_{os.path.basename(video_path)}")

        # Custom compression settings (you can make these configurable via commands)
        crf = 28  # Lower CRF = better quality, higher CRF = more compression
        preset = "medium"  # Slower preset = better compression, faster preset = faster processing

        if compress_video(video_path, compressed_video_path, crf=crf, preset=preset):
            await message.reply("📤 Uploading compressed video...")
            await message.reply_video(compressed_video_path, caption="Here's your compressed video!")
            await message.reply("✅ Done!")
        else:
            await message.reply("❌ Failed to compress the video.")

        # Clean up files
        os.remove(video_path)
        os.remove(compressed_video_path)
    except Exception as e:
        logging.error(f"Error handling video: {e}")
        await message.reply("❌ An error occurred while processing the video.")

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Start command handler."""
    await message.reply("👋 Hi! Send me a video, and I'll compress it for you.")

# Start the bot
if __name__ == "__main__":
    logging.info("Starting bot...")
    app.run()
