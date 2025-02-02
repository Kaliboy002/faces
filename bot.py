import os
import asyncio
import httpx
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from gradio_client import Client as GradioClient, file
from concurrent.futures import ThreadPoolExecutor

# Bot credentials
API_ID = 15787995  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash
BOT_TOKEN = "7844051995:AAHqeWncuLftLXDHIMafOH_bkl3zGxkIbGg"  # Replace with your Telegram Bot Token
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"  # Replace with your imgBB API key

# API endpoints
BG_REMOVE_APIS = [
    "https://for-free.serv00.net/ai-removebg.php?image=",
    "https://ar-api-08uk.onrender.com/remove?bg="
]
ENHANCE_APIS = [
    "https://ar-api-08uk.onrender.com/remini?url=",
    "https://api.nyxs.pw/tools/hd?url="
]

# Gradio Face Swap APIs
FACE_SWAP_APIS = [
    "Kaliboy0012/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro"
]

# Initialize Pyrogram bot
app = Client("image_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store user selections and data
user_selections = {}
user_data = {}

# Thread pool for blocking tasks
executor = ThreadPoolExecutor(max_workers=4)

# Send selection buttons
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Remove Background", callback_data="remove_bg")],
        [InlineKeyboardButton("✨ Enhance Photo", callback_data="enhance_photo")],
        [InlineKeyboardButton("👤 Face Swap", callback_data="face_swap")]
    ])

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user_selections[message.from_user.id] = None  # Reset selection
    await message.reply_text("Welcome! Choose an option:", reply_markup=get_main_buttons())

@app.on_callback_query()
async def button_handler(client: Client, callback_query):
    user_choice = callback_query.data
    user_id = callback_query.from_user.id

    if user_choice == "back":
        await callback_query.message.delete()
        await callback_query.message.reply_text("Welcome! Choose an option:", reply_markup=get_main_buttons())
        return

    user_selections[user_id] = user_choice

    if user_choice == "face_swap":
        user_data[user_id] = {"step": "awaiting_source"}
        await callback_query.message.delete()
        await callback_query.message.reply_text("📷 Send the source image (face to swap).")
    else:
        image_url = (
            "https://i.imghippo.com/files/eNXe4934iU.jpg" if user_choice == "remove_bg"
            else "https://files.catbox.moe/utlaxp.jpg"
        )
        description = (
            "📷 Send a photo to remove its background!" if user_choice == "remove_bg"
            else "✨ Send a photo to enhance it!"
        )
        await callback_query.message.delete()
        await callback_query.message.reply_photo(
            image_url,
            caption=description,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )

@app.on_message(filters.photo)
async def photo_handler(client: Client, message: Message):
    user_id = message.from_user.id
    user_choice = user_selections.get(user_id)

    if not user_choice:
        await message.reply_text("Please select an option first.", reply_markup=get_main_buttons())
        return

    if user_choice == "face_swap":
        await handle_face_swap(client, message)
    else:
        api_list = ENHANCE_APIS if user_choice == "enhance_photo" else BG_REMOVE_APIS
        await process_photo(client, message, api_list)

async def handle_face_swap(client: Client, message: Message):
    user_id = message.from_user.id
    user_state = user_data.get(user_id, {})

    if user_state.get("step") == "awaiting_source":
        # Save source photo
        source_path = await download_photo(client, message)
        user_data[user_id] = {"step": "awaiting_target", "source_path": source_path}
        await message.reply_text("📷 Now send the target image (destination face).")
    elif user_state.get("step") == "awaiting_target":
        # Save target photo
        target_path = await download_photo(client, message)
        user_data[user_id]["target_path"] = target_path
        await message.reply_text("🔄 Processing face swap, please wait...")

        # Perform face swap in a separate thread to avoid blocking
        try:
            swapped_image_path = await asyncio.to_thread(
                perform_face_swap, user_data[user_id]["source_path"], user_data[user_id]["target_path"]
            )
            if swapped_image_path:
                await message.reply_photo(swapped_image_path, caption="✅ Face swap completed!")
            else:
                await message.reply_text("❌ Face swap failed. Please try again.")
        except Exception as e:
            print(f"Face swap error: {e}")
            await message.reply_text("❌ An error occurred during face swap. Please try again.")

        # Cleanup
        cleanup_files(user_id)
        user_data.pop(user_id, None)

async def process_photo(client: Client, message: Message, api_list):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_path = temp_file.name

    try:
        await message.download(temp_path)
        imgbb_url = await upload_to_imgbb(temp_path)
        if not imgbb_url:
            await message.reply_text("❌ Failed to upload image. Please try again.")
            return

        processed_url = await process_image(imgbb_url, api_list)
        if not processed_url:
            await message.reply_text("❌ Processing failed. Try another image.")
            return

        await message.reply_photo(processed_url, caption="✅ Done!")

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("❌ An error occurred. Try again.")

    finally:
        os.remove(temp_path)  # Cleanup temp file

async def download_photo(client: Client, message: Message):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_path = temp_file.name
    await message.download(temp_path)
    return temp_path

def perform_face_swap(source_path, target_path):
    for api_name in FACE_SWAP_APIS:
        try:
            client = GradioClient(api_name)
            result = client.predict(
                source_file=file(source_path),
                target_file=file(target_path),
                doFaceEnhancer=True,
                api_name="/predict"
            )
            return result
        except Exception as e:
            print(f"Face swap API {api_name} failed: {e}")
    return None

async def upload_to_imgbb(image_path):
    try:
        with open(image_path, "rb") as file:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.imgbb.com/1/upload",
                    files={"image": file},
                    data={"key": IMGBB_API_KEY},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()["data"]["url"]
        return None
    except:
        return None

async def process_image(image_url, api_list):
    async with httpx.AsyncClient() as client:
        for api_url in api_list:
            try:
                response = await client.get(f"{api_url}{image_url}", timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success" or data.get("status") == 200:
                        return data["results"][0]["image"] if "results" in data else data["result"]
            except:
                continue
    return None

def cleanup_files(user_id):
    if user_id in user_data:
        for key in ["source_path", "target_path"]:
            if key in user_data[user_id] and os.path.exists(user_data[user_id][key]):
                os.remove(user_data[user_id][key])

if __name__ == "__main__":
    print("Bot started...")
    app.run()
