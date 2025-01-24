import telebot
from telebot.async_telebot import AsyncTeleBot  # Asynchronous TeleBot
import aiohttp
import aiofiles
from gradio_client import Client, file
import os
import asyncio

# Telegram Bot Token
BOT_TOKEN = "7844051995:AAG0yvKGMjwHCajxDmzN6O47rcjd4SOzJOw"  # Replace with your token
bot = AsyncTeleBot(BOT_TOKEN)

# Admin Chat ID
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID

# List of Gradio Clients
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    # Add your API clients here...
]

current_client_index = 0
user_data = {}  # Temporary storage for user data
queue = asyncio.Queue()  # Async processing queue


def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])


def switch_client():
    """Switch to the next API client."""
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)


async def download_file(file_id, save_as):
    """Asynchronously download a file from Telegram."""
    try:
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    async with aiofiles.open(save_as, "wb") as f:
                        await f.write(await response.read())
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")


async def upload_to_catbox(file_path):
    """Asynchronously upload a file to Catbox."""
    try:
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(file_path, "rb") as f:
                response = await session.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": await f.read()},
                )
                response.raise_for_status()
                return (await response.text()).strip()
    except Exception as e:
        raise Exception(f"Failed to upload file to Catbox: {e}")


@bot.message_handler(commands=["start"])
async def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    await bot.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")


@bot.message_handler(content_types=["photo"])
async def handle_photo(message):
    chat_id = message.chat.id

    if chat_id not in user_data:
        await bot.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = message.photo[-1].file_id
            source_image = f"{chat_id}_source.jpg"
            await download_file(file_id, source_image)
            user_data[chat_id]["source_image"] = source_image
            user_data[chat_id]["step"] = "awaiting_target"
            await bot.send_message(chat_id, "Great! Now send the target image (destination face).")

        elif step == "awaiting_target":
            file_id = message.photo[-1].file_id
            target_image = f"{chat_id}_target.jpg"
            await download_file(file_id, target_image)
            user_data[chat_id]["target_image"] = target_image
            await bot.send_message(chat_id, "Your request is being processed. Please wait...")

            # Add task to queue
            await queue.put((chat_id, user_data[chat_id]))

    except Exception as e:
        await bot.send_message(ADMIN_CHAT_ID, f"Error: {e}")
        reset_user_data(chat_id)


async def process_queue():
    """Asynchronously process the face swap queue."""
    while True:
        chat_id, data = await queue.get()
        try:
            client = get_client()
            result = client.predict(
                source_file=file(data["source_image"]),
                target_file=file(data["target_image"]),
                doFaceEnhancer=True,
                api_name="/predict"
            )

            swapped_image_url = await upload_to_catbox(result)

            # Send result to the user
            async with aiofiles.open(result, "rb") as swapped_file:
                await bot.send_photo(chat_id, swapped_file, caption=f"Face-swapped image: {swapped_image_url}")

        except Exception as e:
            await bot.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
            switch_client()

        finally:
            # Clean up files and reset user data
            cleanup_files(chat_id)
            reset_user_data(chat_id)
            queue.task_done()


def cleanup_files(chat_id):
    """Clean up temporary files."""
    for key in ["source_image", "target_image"]:
        if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
            os.remove(user_data[chat_id][key])


def reset_user_data(chat_id):
    """Reset user data."""
    if chat_id in user_data:
        user_data.pop(chat_id, None)


# Start processing the queue in the background
asyncio.create_task(process_queue())

# Run the bot
bot.infinity_polling()
