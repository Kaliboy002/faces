import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
import ffmpeg
import asyncio

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Environment Variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Validate environment variables
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logging.error("Missing environment variables: API_ID, API_HASH, or BOT_TOKEN")
    exit(1)

# Initialize Pyrogram Client with increased timeouts
app = Client(
    "video_compressor_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=4,  # Increase workers for better performance
    workdir="sessions",
)

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
    await message.edit_text(f"🔧 Compressing... {int(progress * 100)}%")

@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
    """Handle incoming video files."""
    try:
        # Notify the user
        status_message = await message.reply("📥 Downloading video...")

        # Download the video with a longer timeout
        video_path = await message.download(block=True, progress=send_progress, progress_args=(status_message,))

        # Notify the user
        await status_message.edit_text("🔧 Compressing video...")

        # Determine compression settings based on file size
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
        if file_size > 30:  # For videos larger than 30 MB, use faster settings
            crf = 30
            preset = "fast"
        else:
            crf = 28
            preset = "medium"

        # Compress the video
        compressed_video_path = os.path.join(COMPRESSED_VIDEO_DIR, f"compressed_{os.path.basename(video_path)}")
        if compress_video(video_path, compressed_video_path, crf=crf, preset=preset):
            await status_message.edit_text("📤 Uploading compressed video...")
            await message.reply_video(compressed_video_path, caption="Here's your compressed video!")
            await status_message.edit_text("✅ Done!")
        else:
            await status_message.edit_text("❌ Failed to compress the video.")

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
