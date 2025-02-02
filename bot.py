import os
import requests
from gradio_client import Client, file
from pyrogram import Client as PyroClient, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Telegram Bot Token and API Information
API_ID = "15787995"  # Replace with your API ID
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"  # Replace with your API Hash
BOT_TOKEN = "7844051995:AAHqeWncuLftLXDHIMafOH_bkl3zGxkIbGg"  # Replace with your Telegram Bot Token
ADMIN_CHAT_ID = 7046488481  # Replace with your Telegram user ID

# Pyrogram Bot Initialization
app = PyroClient("image_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# API URLs for Background Removal and Enhancement
BG_REMOVE_APIS = [
    "https://for-free.serv00.net/ai-removebg.php?image=",
    "https://ar-api-08uk.onrender.com/remove?bg="
]

ENHANCE_APIS = [
    "https://ar-api-08uk.onrender.com/remini?url=",
    "https://api.nyxs.pw/tools/hd?url="
]

# List of Gradio Clients for Face Swap APIs
api_clients = [
    "Kaliboy0012/face-swapm",
    "Jonny001/Image-Face-Swap",
    "ovi054/face-swap-pro"
]
current_client_index = 0
user_data = {}

def get_client():
    global current_client_index
    return Client(api_clients[current_client_index])

def switch_client():
    global current_client_index
    current_client_index = (current_client_index + 1) % len(api_clients)

def download_file(client, file_id, save_as):
    try:
        file_path = client.download_media(file_id, file_name=save_as)
        return file_path
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")

def upload_to_catbox(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f}
            )
            response.raise_for_status()
            return response.text.strip()
    except Exception as e:
        raise Exception(f"Failed to upload file to Catbox: {e}")

# Send main menu with options
def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Remove Background", callback_data="remove_bg")],
        [InlineKeyboardButton("✨ Enhance Photo", callback_data="enhance_photo")],
        [InlineKeyboardButton("🤖 Face Swap", callback_data="face_swap")]
    ])

@app.on_message(filters.command("start"))
def start(client, message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "awaiting_source"}
    client.send_message(chat_id, "Welcome! Choose an option:", reply_markup=get_main_buttons())

@app.on_callback_query()
def button_handler(client, callback_query):
    user_choice = callback_query.data
    chat_id = callback_query.from_user.id
    if user_choice == "back":
        client.send_message(chat_id, "Choose an option:", reply_markup=get_main_buttons())
        return

    user_data[chat_id] = {"step": "awaiting_source", "action": user_choice}

    image_url = "https://i.imghippo.com/files/eNXe4934iU.jpg" if user_choice == "remove_bg" else "https://files.catbox.moe/utlaxp.jpg"
    description = "📷 Send a photo to remove its background!" if user_choice == "remove_bg" else "✨ Send a photo to enhance it!" if user_choice == "enhance_photo" else "🤖 Send a photo for face swap!"
    
    client.send_message(chat_id, description, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]]))
    client.send_photo(chat_id, image_url, caption="Choose action", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]]))

@app.on_message(filters.photo)
def handle_photo(client, message):
    chat_id = message.chat.id
    user_choice = user_data.get(chat_id, {}).get("action")
    if not user_choice:
        client.send_message(chat_id, "Please select an option first.", reply_markup=get_main_buttons())
        return

    step = user_data[chat_id].get("step")
    try:
        if step == "awaiting_source":
            file_id = message.photo.file_id
            source_image_path = f"{chat_id}_source.jpg"
            user_data[chat_id]["source_image"] = download_file(client, file_id, source_image_path)
            user_data[chat_id]["step"] = "awaiting_target"
            client.send_message(chat_id, "Now send the target image (destination face) for face swap." if user_choice == "face_swap" else "Great! Now send the target image (destination face).")
        
        elif step == "awaiting_target":
            if "source_image" not in user_data[chat_id]:
                client.send_message(chat_id, "Source image is missing. Please restart with /start.")
                reset_user_data(chat_id)
                return
            
            file_id = message.photo.file_id
            target_image_path = f"{chat_id}_target.jpg"
            user_data[chat_id]["target_image"] = download_file(client, file_id, target_image_path)
            client.send_message(chat_id, "Processing your request, please wait...")

            # Process the Face Swap, Background Removal, or Enhancement based on the user choice
            if user_choice == "face_swap":
                process_face_swap(client, chat_id)
            elif user_choice == "remove_bg":
                process_remove_bg(client, chat_id)
            else:
                process_enhance(client, chat_id)
            
    except Exception as e:
        client.send_message(ADMIN_CHAT_ID, f"Unexpected error: {e}")
        reset_user_data(chat_id)

def process_face_swap(client, chat_id):
    try:
        source_image = user_data[chat_id]["source_image"]
        target_image = user_data[chat_id]["target_image"]

        client_api = get_client()
        result = client_api.predict(
            source_file=file(source_image),
            target_file=file(target_image),
            doFaceEnhancer=True,
            api_name="/predict"
        )
        swapped_image_url = upload_to_catbox(result)
        client.send_photo(chat_id, photo=result, caption="🤖 Face-swapped image:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]]))
    except Exception as e:
        client.send_message(ADMIN_CHAT_ID, f"Face Swap Error: {e}")
        client.send_message(chat_id, "❌ Error processing face swap. Please try again.")
        reset_user_data(chat_id)

def process_remove_bg(client, chat_id):
    try:
        source_image = user_data[chat_id]["source_image"]
        image_url = await upload_to_imgbb(source_image)
        
        for api_url in BG_REMOVE_APIS:
            try:
                response = requests.get(f"{api_url}{image_url}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] == "success":
                        removed_image_url = result["results"][0]["image"]
                        client.send_photo(chat_id, photo=removed_image_url, caption="✅ Background Removed!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]]))
                        return
            except Exception as e:
                continue
        client.send_message(chat_id, "❌ Failed to remove background, please try again.")
        reset_user_data(chat_id)
    except Exception as e:
        client.send_message(chat_id, f"❌ Error: {e}")
        reset_user_data(chat_id)

def process_enhance(client, chat_id):
    try:
        source_image = user_data[chat_id]["source_image"]
        image_url = await upload_to_imgbb(source_image)
        
        for api_url in ENHANCE_APIS:
            try:
                response = requests.get(f"{api_url}{image_url}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] == "success":
                        enhanced_image_url = result["results"][0]["image"]
                        client.send_photo(chat_id, photo=enhanced_image_url, caption="✨ Enhanced Photo!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]]))
                        return
            except Exception as e:
                continue
        client.send_message(chat_id, "❌ Failed to enhance photo, please try again.")
        reset_user_data(chat_id)
    except Exception as e:
        client.send_message(chat_id, f"❌ Error: {e}")
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
