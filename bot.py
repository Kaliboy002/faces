import os
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from gradio_client import Client, file
import aiohttp

# Telegram Bot Token
BOT_TOKEN = "7844051995:AAG0yvKGMjwHCajxDmzN6O47rcjd4SOzJOw"  # Replace with your bot token
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Admin Chat ID
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID

# Gradio API Clients
api_clients = [
    "Kaliboy002/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro",
    # Add more API clients if needed
]

current_client_index = 0
user_data = {}  # Temporary storage for user data


# Get the current Gradio client
def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])


# Switch to the next API client
def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)


# Asynchronously download a file from Telegram
async def download_file(file_id: str, save_as: str):
    try:
        file_info = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    with open(save_as, "wb") as f:
                        f.write(await response.read())
                else:
                    raise Exception(f"Failed to download file. HTTP {response.status}")
    except Exception as e:
        raise Exception(f"Error downloading file: {e}")


# Asynchronously upload a file to Catbox
async def upload_to_catbox(file_path: str):
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = {"reqtype": "fileupload"}
                files = {"fileToUpload": f}
                async with session.post("https://catbox.moe/user/api.php", data=data, files=files) as response:
                    if response.status == 200:
                        return (await response.text()).strip()
                    else:
                        raise Exception(f"Failed to upload to Catbox. HTTP {response.status}")
    except Exception as e:
        raise Exception(f"Error uploading to Catbox: {e}")


# Router setup
router = Router()


# Start command
@router.message(Command(commands=["start"]))
async def start(message: Message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    await message.answer("Welcome to the Face Swap Bot! Please send the source image (face to swap).")


# Handle photos sent by the user
@router.message(lambda message: message.photo)
async def handle_photo(message: Message):
    chat_id = message.chat.id

    if chat_id not in user_data:
        await message.answer("Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = message.photo[-1].file_id
            source_image = f"{chat_id}_source.jpg"
            await download_file(file_id, source_image)
            user_data[chat_id]["source_image"] = source_image
            user_data[chat_id]["step"] = "awaiting_target"
            await message.answer("Great! Now send the target image (destination face).")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                await message.answer("Source image is missing. Please restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = message.photo[-1].file_id
            target_image = f"{chat_id}_target.jpg"
            await download_file(file_id, target_image)
            user_data[chat_id]["target_image"] = target_image
            await message.answer("Processing your request. Please wait...")

            # Perform the face swap
            while True:
                try:
                    client = get_client()
                    source_file = user_data[chat_id]["source_image"]
                    target_file = user_data[chat_id]["target_image"]

                    result = client.predict(
                        source_file=file(source_file),
                        target_file=file(target_file),
                        doFaceEnhancer=True,
                        api_name="/predict",
                    )

                    # Upload to Catbox and get the URL
                    swapped_image_url = await upload_to_catbox(result)

                    # Send the swapped image to the user
                    swapped_image = FSInputFile(result)
                    await bot.send_photo(chat_id, swapped_image, caption=f"Face-swapped image: {swapped_image_url}")
                    break

                except Exception as e:
                    await bot.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            await message.answer("Invalid step. Please restart with /start.")
            reset_user_data(chat_id)

    except Exception as e:
        await bot.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)


# Reset user data
def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)


# Clean up temporary files
def cleanup_files(chat_id):
    if chat_id in user_data:
        for key in ["source_image", "target_image"]:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])


# Application startup
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
