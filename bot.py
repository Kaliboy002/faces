import os
import logging
import subprocess
import asyncio
import imageio
from pyrogram import Client, filters
from pyrogram.types import Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Configuration
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"  # Replace with your Bot Token

# Pyrogram Bot Initialization
app = Client("video_compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary directory for storing files
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Function to get FFmpeg executable
def get_ffmpeg():
    return imageio.plugins.ffmpeg.get_exe()

# Function to compress video using FFmpeg
async def compress_video(input_path: str, output_path: str) -> bool:
    """
    Compresses a video using FFmpeg asynchronously while maintaining quality.
    Args:
        input_path: Path to the input video file.
        output_path: Path to save the compressed video file.
    Returns:
        bool: True if compression is successful, False otherwise.
    """
    try:
        ffmpeg_path = get_ffmpeg()
        
        # FFmpeg command to compress video
        command = [
            ffmpeg_path,
            "-i", input_path,  # Input file
            "-vf", "scale='min(1280,iw)':-2",  # Resize to max width of 1280px, maintain aspect ratio
            "-c:v", "libx264",  # Use H.264 codec
            "-crf", "24",  # Constant Rate Factor (lower = better quality, higher = smaller size)
            "-preset", "fast",  # Faster compression for quick processing
            "-c:a", "aac",  # Re-encode audio to AAC for compatibility
            "-b:a", "128k",  # Set audio bitrate
            output_path
        ]

        # Run the FFmpeg command asynchronously
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Wait for the process to complete
        await process.wait()

        # Check if process completed successfully
        return process.returncode == 0
    except Exception as e:
        logger.error(f"Error compressing video: {e}")
        return False

# Start command handler
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """Handles the /start command."""
    await message.reply_text(
        "🎥 Welcome to the Video Compressor Bot!\n\n"
        "Send me a video file, and I will compress it for you while maintaining quality."
    )

# Video message handler
@app.on_message(filters.video)
async def handle_video(client: Client, message: Message):
    """Handles video files and compresses them."""
    try:
        # Notify the user that the video is being processed
        status_msg = await message.reply_text("⏳ Processing your video...")

        # Download the video file asynchronously
        video_path = await message.download(file_name=os.path.join(TEMP_DIR, f"input_video_{message.id}.mp4"))

        # Define the output path for the compressed video
        output_path = os.path.join(TEMP_DIR, f"compressed_video_{message.id}.mp4")

        # Compress the video asynchronously
        if await compress_video(video_path, output_path):
            # Send the compressed video back to the user
            await message.reply_video(
                video=output_path,
                caption="✅ Here is your compressed video!",
                reply_to_message_id=message.id
            )
            await status_msg.delete()  # Delete the status message
        else:
            await message.reply_text("❌ Failed to compress the video. Please try again.")

        # Clean up temporary files
        os.remove(video_path)
        os.remove(output_path)
    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await message.reply_text("⚠️ An error occurred. Please try again.")

# Run the bot
if __name__ == "__main__":
    logger.info("Starting Video Compressor Bot...")
    app.run()
