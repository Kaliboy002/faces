import os
import asyncio
import httpx
import tempfile
import motor.motor_asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from gradio_client import Client as GradioClient, file, handle_file
from concurrent.futures import ThreadPoolExecutor

# Bot credentials
API_ID = 15787995
API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
BOT_TOKEN = "7817420437:AAH5z1PnmDOd4w-viRAqCIuGSDiUKYzQ--Y"
IMGBB_API_KEY = "b34225445e8edd8349d8a9fe68f20369"

# Admin chat ID
ADMIN_CHAT_ID = 7046488481  # Replace with the actual admin chat ID

# MongoDB connection
MONGO_URI = "mongodb+srv://Kali:SHM14002022SHM@cluster0.bxsct.mongodb.net/myDatabase?retryWrites=true&w=majority"
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = mongo_client.shah
users_col = db.users

# API endpoints
BG_REMOVE_APIS = [
    "https://for-free.serv00.net/ai-removebg.php?image=",
    "https://ar-api-08uk.onrender.com/remove?bg="
]
ENHANCE_APIS = [
    "https://ar-api-08uk.onrender.com/remini?url=",
    "https://api.nyxs.pw/tools/hd?url="
]
FACE_ENHANCE_API = "byondxr/finegrain-image-enhancer"

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
processing_users = set()  # To track processing users
processing_face_swaps = set()  # To track face swap processing users

# Thread pool for blocking tasks
executor = ThreadPoolExecutor(max_workers=4)

def get_main_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Remove Background", callback_data="remove_bg")],
        [InlineKeyboardButton("✨ Enhance Photo", callback_data="enhance_photo")],
        [InlineKeyboardButton("👤 Face Swap", callback_data="face_swap")],
        [InlineKeyboardButton("🖼 AI Face Edit", callback_data="ai_face_edit")]
    ])

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    # Fake mandatory join message
    join_message = "To use this bot, you must join our channel."
    join_button = InlineKeyboardButton("Join", url="https://t.me/Kali_Linux_BOTS")
    check_button = InlineKeyboardButton("Check", callback_data='check_join')
    join_markup = InlineKeyboardMarkup([[join_button], [check_button]])
    
    await message.reply_text(join_message, reply_markup=join_markup)

@app.on_callback_query(filters.regex("check_join"))
async def check_join_handler(client: Client, callback_query):
    user_id = callback_query.from_user.id

    await callback_query.message.delete()
    
    # After checking, show the main menu
    user = await users_col.find_one({"_id": user_id})
    if not user:
        referrer_id = None
        if len(callback_query.message.text.split()) > 1 and callback_query.message.text.split()[1].isdigit():
            referrer_id = int(callback_query.message.text.split()[1])
        user_doc = {
            "_id": user_id,
            "name": callback_query.from_user.first_name,
            "face_swaps_left": 2,
            "invites_sent": 0,
            "referrals": [],
            "referral_link": f"https://t.me/{BOT_TOKEN.split(':')[0]}?start={user_id}"
        }
        if referrer_id:
            user_doc["referrer"] = referrer_id
            await users_col.update_one(
                {"_id": referrer_id},
                {"$inc": {"face_swaps_left": 1, "invites_sent": 1}}
            )
            try:
                await app.send_message(
                    referrer_id,
                    f"🎉 User {callback_query.from_user.first_name} started the bot using your referral link! You've received 1 additional face swap."
                )
            except:
                pass
        await users_col.insert_one(user_doc)
        await callback_query.message.reply_text("Welcome! Choose an option:", reply_markup=get_main_buttons())
    else:
        await callback_query.message.reply_text("Welcome back! Choose an option:", reply_markup=get_main_buttons())

@app.on_message(filters.command("add") & filters.user(ADMIN_CHAT_ID))
async def add_handler(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.reply_text("❌ Invalid format. Use: /add <user_id> <amount>")
            return

        target_user_id = int(args[1])
        amount = int(args[2])

        result = await users_col.update_one(
            {"_id": target_user_id},
            {"$inc": {"face_swaps_left": amount}}
        )

        if result.matched_count > 0:
            await message.reply_text(f"✅ Successfully added {amount} face swap attempts to user {target_user_id}.")
        else:
            await message.reply_text(f"❌ User {target_user_id} not found.")
    except ValueError:
        await message.reply_text("❌ Invalid input. User ID and amount must be numbers.")
    except Exception as e:
        await message.reply_text(f"❌ An error occurred: {e}")

@app.on_message(filters.command("reset") & filters.user(ADMIN_CHAT_ID))
async def reset_handler(client: Client, message: Message):
    try:
        await users_col.delete_many({})
        await message.reply_text("✅ All user data has been reset.")
    except Exception as e:
        await message.reply_text(f"❌ An error occurred: {e}")

@app.on_callback_query()
async def button_handler(client: Client, callback_query):
    user_choice = callback_query.data
    user_id = callback_query.from_user.id

    if user_choice == "back":
        await callback_query.message.delete()
        await callback_query.message.reply_text("Welcome! Choose an option:", reply_markup=get_main_buttons())
        return
    elif user_choice == "processed_back":
        await callback_query.message.reply_text("Welcome! Choose an option:", reply_markup=get_main_buttons())
        return

    user_selections[user_id] = user_choice

    if user_choice == "face_swap":
        user = await users_col.find_one({"_id": user_id})
        if user["face_swaps_left"] <= 0:
            await callback_query.message.reply_text(
                f"❌ You've used all your free face swaps.\n\n"
                f"Your referral link: {user['referral_link']}\n"
                f"Face swaps left: {user['face_swaps_left']}\n"
                f"Invites sent: {user['invites_sent']}\n"
                f"Share your referral link to get more swaps!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back")]
                ])
            )
            return

        await callback_query.message.delete()
        await callback_query.message.reply_photo(
            "https://i.imghippo.com/files/iDxy5739tZs.jpg",
            caption="📷 Send the source image (face to swap).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        user_data[user_id] = {"step": "awaiting_source"}
    elif user_choice == "ai_face_edit":
        await callback_query.message.delete()
        await callback_query.message.reply_photo(
            "https://i.imghippo.com/files/iDxy5739tZs.jpg",
            caption="📷 Send a photo for AI Face Edit!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
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
        if user_id in processing_face_swaps:
            await message.reply_text("❌ Your face swap is already being processed. Please wait and try again later.")
            return
        processing_face_swaps.add(user_id)
        await handle_face_swap(client, message)
        processing_face_swaps.remove(user_id)
    elif user_choice == "ai_face_edit":
        if user_id in processing_users:
            await message.reply_text("❌ Your photo is already being processed. Please wait and try again later.")
            return
        processing_users.add(user_id)
        await message.reply_text("🔄 Processing photo, please wait...")
        await process_ai_face_edit(client, message)
        processing_users.remove(user_id)
    else:
        if user_id in processing_users:
            await message.reply_text("❌ Your photo is already being processed. Please wait and try again later.")
            return
        processing_users.add(user_id)
        try:
            await message.reply_text("🔄 Processing photo, please wait...")
            api_list = ENHANCE_APIS if user_choice == "enhance_photo" else BG_REMOVE_APIS
            await process_photo(client, message, api_list)
        finally:
            processing_users.remove(user_id)

async def handle_face_swap(client: Client, message: Message):
    user_id = message.from_user.id
    user_state = user_data.get(user_id, {})

    user = await users_col.find_one({"_id": user_id})
    if user["face_swaps_left"] <= 0:
        await message.reply_text(
            f"❌ You've used all your free face swaps.\n\n"
            f"Your referral link: {user['referral_link']}\n"
            f"Face swaps left: {user['face_swaps_left']}\n"
            f"Invites sent: {user['invites_sent']}\n"
            f"Share your referral link to get more swaps!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        return

    if user_state.get("step") == "awaiting_source":
        source_path = await download_photo(client, message)
        user_data[user_id] = {"step": "awaiting_target", "source_path": source_path}
        await message.reply_text("📷 Now send the target image (destination face).")
    elif user_state.get("step") == "awaiting_target":
        target_path = await download_photo(client, message)
        user_data[user_id]["target_path"] = target_path

        await message.reply_text("🔄 Processing photo, please wait...")

        try:
            swapped_image_path = await asyncio.to_thread(
                perform_face_swap, user_data[user_id]["source_path"], user_data[user_id]["target_path"]
            )
            if swapped_image_path:
                await message.reply_photo(
                    swapped_image_path,
                    caption="✅ Face swap completed!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="processed_back")]
                    ])
                )
                await users_col.update_one(
                    {"_id": user_id},
                    {"$inc": {"face_swaps_left": -1}}
                )
            else:
                await message.reply_text("❌ Face swap failed. Please try again.")
        except Exception as e:
            print(f"Face swap error: {e}")
            await message.reply_text("❌ An error occurred during face swap. Please try again.")
        finally:
            cleanup_files(user_id)
            user_data.pop(user_id, None)

async def process_ai_face_edit(client: Client, message: Message):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_path = temp_file.name

    try:
        await message.download(temp_path)
        enhanced_path = await asyncio.to_thread(enhance_image, temp_path)
        
        if not enhanced_path:
            await message.reply_text("❌ AI Face Edit failed. Try another image.")
            return

        # Ensure the enhanced image has a valid extension
        valid_extension_path = enhanced_path + ".jpg"
        os.rename(enhanced_path, valid_extension_path)

        await message.reply_photo(
            valid_extension_path,
            caption="✅ AI Face Edit completed!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="processed_back")]
            ])
        )

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("❌ An error occurred. Try again.")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

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

        await message.reply_photo(
            processed_url,
            caption="✅ Done!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="processed_back")]
            ])
        )

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("❌ An error occurred. Try again.")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

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
                    elif data.get("status") is True and "result" in data:
                        return data["result"]
            except:
                continue
    return None

def enhance_image(image_path):
    for api_name in [FACE_ENHANCE_API]:
        try:
            client = GradioClient(api_name)
            result = client.predict(
                input_image=handle_file(image_path),
                prompt="",
                negative_prompt="makeup, lipstick, eyeliner, smooth skin, unrealistic face",
                seed=42,
                upscale_factor=2,
                controlnet_scale=0.3,
                controlnet_decay=1,
                condition_scale=3,
                tile_width=128,
                tile_height=128,
                denoise_strength=0.25,
                num_inference_steps=15,
                solver="DPMSolver",
                api_name="/process"
            )
            enhanced_image_path = result[1]
            return enhanced_image_path
        except Exception as e:
            print(f"Enhance image error: {e}")
    return None

def cleanup_files(user_id):
    if user_id in user_data:
        for key in ["source_path", "target_path"]:
            if key in user_data[user_id] and os.path.exists(user_data[user_id][key]):
                os.remove(user_data[user_id][key])

if __name__ == "__main__":
    print("Bot started...")
    app.run()
