import os
import httpx
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from gradio_client import Client as GradioClient, file

# Bot credentials
API_ID = 15787995  
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  
BOT_TOKEN = "7844051995:AAGQAcxdvFs7Xq_Szji5gMRndZpyt6_jn0c"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"

# Face swap API clients
FACE_SWAP_APIS = [
    "Kaliboy0012/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro"
]
current_client_index = 0

# API endpoints
BG_REMOVE_APIS = [
    "https://for-free.serv00.net/ai-removebg.php?image=",
    "https://ar-api-08uk.onrender.com/remove?bg="
]
ENHANCE_APIS = [
    "https://ar-api-08uk.onrender.com/remini?url=",
    "https://api.nyxs.pw/tools/hd?url="
]

# Fixed image URLs
BG_REMOVE_IMAGE = "https://i.imghippo.com/files/eNXe4934iU.jpg"
ENHANCE_IMAGE = "https://files.catbox.moe/utlaxp.jpg"
FACE_SWAP_IMAGE = "https://i.imghippo.com/files/example_faceswap.jpg"

# Initialize Pyrogram bot
app = Client("image_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store user selections
user_selections = {}

# Get the current API client for face swap
def get_face_swap_client():
    global current_client_index
    return GradioClient(FACE_SWAP_APIS[current_client_index])

# Switch to the next API client for face swap
def switch_face_swap_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(FACE_SWAP_APIS)

# Send selection buttons
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Remove Background", callback_data="remove_bg")],
        [InlineKeyboardButton("✨ Enhance Photo", callback_data="enhance_photo")],
        [InlineKeyboardButton("😎 Face Swap", callback_data="face_swap")]
    ])

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user_selections[message.from_user.id] = None  # Reset selection
    await message.reply_text(
        "Welcome! Choose an option:",
        reply_markup=get_main_buttons()
    )

@app.on_callback_query()
async def button_handler(client: Client, callback_query):
    user_choice = callback_query.data
    if user_choice == "back":
        await callback_query.message.delete()
        await callback_query.message.reply_text(
            "Welcome! Choose an option:",
            reply_markup=get_main_buttons()
        )
        return

    user_selections[callback_query.from_user.id] = {"choice": user_choice}

    if user_choice == "remove_bg":
        image_url, description = BG_REMOVE_IMAGE, "📷 Send a photo to remove its background!"
    elif user_choice == "enhance_photo":
        image_url, description = ENHANCE_IMAGE, "✨ Send a photo to enhance it!"
    elif user_choice == "face_swap":
        image_url, description = FACE_SWAP_IMAGE, "😎 Send the **source image** (face to swap)."

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
    user_choice = user_selections.get(message.from_user.id)

    if not user_choice:
        await message.reply_text("Please select an option first.", reply_markup=get_main_buttons())
        return

    choice = user_choice.get("choice")

    if choice == "face_swap":
        if "source" not in user_choice:
            user_selections[message.from_user.id]["source"] = message.photo.file_id
            await message.reply_text("Now send the **target image**.")
        else:
            user_selections[message.from_user.id]["target"] = message.photo.file_id
            await process_face_swap(client, message)

    else:
        api_list = ENHANCE_APIS if choice == "enhance_photo" else BG_REMOVE_APIS

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

async def process_face_swap(client: Client, message: Message):
    user_choice = user_selections.get(message.from_user.id)
    if "source" not in user_choice or "target" not in user_choice:
        await message.reply_text("❌ Missing images. Please restart with 'Face Swap'.")
        return

    source_path = await download_telegram_photo(client, user_choice["source"])
    target_path = await download_telegram_photo(client, user_choice["target"])

    try:
        while True:
            try:
                client_api = get_face_swap_client()
                result = await asyncio.to_thread(client_api.predict,
                                                 source_file=file(source_path),
                                                 target_file=file(target_path),
                                                 doFaceEnhancer=True,
                                                 api_name="/predict")
                if result:
                    break
            except:
                switch_face_swap_client()

        swapped_url = await upload_to_imgbb(result)
        await message.reply_photo(swapped_url, caption="✅ Face Swapped Successfully!")

    except Exception as e:
        await message.reply_text(f"❌ Face swap failed. Error: {e}")

    finally:
        os.remove(source_path)
        os.remove(target_path)
        user_selections.pop(message.from_user.id, None)

async def download_telegram_photo(client: Client, file_id):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_path = temp_file.name
    await client.download_media(file_id, temp_path)
    return temp_path

if __name__ == "__main__":
    print("Bot started...")
    app.run()
