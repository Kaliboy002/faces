import os
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters

# تنظیمات بات
API_ID = int(os.getenv("API_ID", "15787995"))
API_HASH = os.getenv("API_HASH", "e51a3154d2e0c45e5ed70251d68382de")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7844051995:AAHOprIiU0G8ZqBuw6o0zBzcIm-B-74ovK8")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "7046488481"))

app = PyroClient("face_swap_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

api_clients = [
    "Kaliboy0012/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro"
]
current_client_index = 0
user_data = {}
executor = ThreadPoolExecutor(max_workers=4)

def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])

def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)

async def download_file(client, file_id, save_as):
    try:
        return await asyncio.to_thread(client.download_media, file_id, file_name=save_as)
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")

async def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            response = await asyncio.to_thread(requests.post, "https://catbox.moe/user/api.php",
                                               data={"reqtype": "fileupload"},
                                               files={"fileToUpload": f})
            response.raise_for_status()
            return response.text.strip()
    except Exception as e:
        raise Exception(f"Failed to upload file to Catbox: {e}")

@app.on_message(filters.command("start"))
async def start(client, message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    await client.send_message(chat_id, "Welcome! Send the source image (face to swap).")

@app.on_message(filters.photo)
async def handle_photo(client, message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        await client.send_message(chat_id, "Please start the bot using /start.")
        return

    step = user_data[chat_id].get("step", None)

    try:
        if step == "awaiting_source":
            file_id = message.photo.file_id
            source_image_path = f"{chat_id}_source.jpg"
            user_data[chat_id]["source_image"] = await download_file(client, file_id, source_image_path)
            user_data[chat_id]["step"] = "awaiting_target"
            await client.send_message(chat_id, "Now send the target image.")

        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                await client.send_message(chat_id, "Source image is missing. Restart with /start.")
                reset_user_data(chat_id)
                return

            file_id = message.photo.file_id
            target_image_path = f"{chat_id}_target.jpg"
            user_data[chat_id]["target_image"] = await download_file(client, file_id, target_image_path)
            await client.send_message(chat_id, "Processing, please wait...")

            while True:
                try:
                    client_api = get_client()
                    source_file = user_data[chat_id]["source_image"]
                    target_file = user_data[chat_id]["target_image"]

                    result = await asyncio.to_thread(client_api.predict,
                                                     source_file=file(source_file),
                                                     target_file=file(target_file),
                                                     doFaceEnhancer=True,
                                                     api_name="/predict")

                    # ارسال سریع تصویر پردازش‌شده به کاربر
                    await client.send_photo(chat_id, photo=result, caption="Here is your swapped image!")

                    # آپلود در Catbox در پس‌زمینه
                    swapped_image_url = await upload_to_catbox(result)
                    await client.send_message(chat_id, f"Download link: {swapped_image_url}")

                    break

                except Exception as e:
                    await client.send_message(ADMIN_CHAT_ID, f"Error with API {api_clients[current_client_index]}: {e}")
                    switch_client()

            cleanup_files(chat_id)
            reset_user_data(chat_id)

        else:
            await client.send_message(chat_id, "Invalid step. Restart with /start.")
            reset_user_data(chat_id)

    except Exception as e:
        await client.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)

def reset_user_data(chat_id):
    if chat_id in user_data:
        user_data.pop(chat_id, None)

def cleanup_files(chat_id):
    if chat_id in user_data:
        for key in ["source_image", "target_image"]:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])

app.run()
