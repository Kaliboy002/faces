import os
import asyncio
from telebot.async_telebot import AsyncTeleBot
from gradio_client import Client, file
import aiofiles
import aiohttp

# Telegram Bot Token
BOT_TOKEN = "7844051995:AAG0yvKGMjwHCajxDmzN6O47rcjd4SOzJOw"  # Replace with your bot token
bot = AsyncTeleBot(BOT_TOKEN)

# Admin Chat ID
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID

# Gradio API Clients
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro",
    "mrbeliever/Face-Swapper",
    "Alibrown/Advanced-Face-Swaper",
    # Add more APIs if needed...
]

current_client_index = 0
user_data = {}
queue = asyncio.Queue()


# Function to get the current Gradio client
def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])


# Function to switch to the next Gradio client
def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)


# Function to download a file from Telegram
async def download_file(file_id, save_as):
    try:
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    async with aiofiles.open(save_as, "wb") as f:
                        await f.write(await response.read())
                else:
                    raise Exception(f"Failed to download file: {response.status}")
    except Exception as e:
        raise Exception(f"Error in downloading file: {e}")


# Function to handle face swap with Gradio API
async def face_swap(source_path, target_path):
    while True:
        try:
            client = get_client()
            result = client.predict(
                source_file=file(source_path),
                target_file=file(target_path),
                doFaceEnhancer=True,
                api_name="/predict",
            )
            return result  # Path to the swapped file
        except Exception as e:
            switch_client()
            continue


# Start command
@bot.message_handler(commands=["start"])
async def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    await bot.send_message(chat_id, "Welcome to the Face Swap Bot! Please send the source image (face to swap).")


# Handle photos sent by the user
@bot.message_handler(content_types=["photo"])
async def handle_photo(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        await bot.send_message(chat_id, "Please start with /start.")
        return

    step = user_data[chat_id].get("step")

    try:
        if step == "awaiting_source":
            file_id = message.photo[-1].file_id
            source_image = f"{chat_id}_source.jpg"
            await download_file(file_id, source_image)
            user_data[chat_id]["source_image"] = source_image
            user_data[chat_id]["step"] = "awaiting_target"
            await bot.send_message(chat_id, "Got the source image! Now send the target image (destination face).")

        elif step == "awaiting_target":
            file_id = message.photo[-1].file_id
            target_image = f"{chat_id}_target.jpg"
            await download_file(file_id, target_image)
            user_data[chat_id]["target_image"] = target_image
            user_data[chat_id]["step"] = "processing"

            await bot.send_message(chat_id, "Processing your request. Please wait...")

            # Add the task to the queue for processing
            await queue.put((chat_id, user_data[chat_id]))

    except Exception as e:
        await bot.send_message(ADMIN_CHAT_ID, f"Error: {e}")
        reset_user_data(chat_id)


# Process the face swap queue
async def process_queue():
    while True:
        chat_id, data = await queue.get()
        try:
            source_path = data["source_image"]
            target_path = data["target_image"]

            # Perform the face swap
            swapped_image_path = await face_swap(source_path, target_path)

            # Send the result back to the user
            async with aiofiles.open(swapped_image_path, "rb") as swapped_file:
                await bot.send_photo(chat_id, swapped_file)

            # Clean up files
            cleanup_files(chat_id)
        except Exception as e:
            await bot.send_message(ADMIN_CHAT_ID, f"Error during face swap for {chat_id}: {e}")
            await bot.send_message(chat_id, "An error occurred during processing. Please try again.")
        finally:
            reset_user_data(chat_id)
            queue.task_done()


# Clean up temporary files
def cleanup_files(chat_id):
    files_to_remove = ["source_image", "target_image"]
    for key in files_to_remove:
        if key in user_data.get(chat_id, {}) and os.path.exists(user_data[chat_id][key]):
            os.remove(user_data[chat_id][key])


# Reset user data
def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)


# Start processing the queue
asyncio.create_task(process_queue())

# Run the bot
bot.infinity_polling()
