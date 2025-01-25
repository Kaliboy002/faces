from pyrogram import Client, types, filters, enums
import asyncio
import os
import requests
import json
from pymongo import MongoClient
from PIL import Image
import cv2
import numpy as np
import dlib
from io import BytesIO

# MongoDB Connection
client = MongoClient('mongodb+srv://mrshokrullah:L7yjtsOjHzGBhaSR@cluster0.aqxyz.mongodb.net/shah?retryWrites=true&w=majority&appName=Cluster0')  # Use your MongoDB URI here
db = client['shah']  # Create a database
users_collection = db['shm']  # Create a collection for users


# Bot Config Objects
class Config:
    SESSION = "BQG0lX0AqA8ehJYDUzT99Yo_Zh7H4hkEuAc1L9nETnK7pShNlxfCHxFjSCNgNR6a6oik70m8-OD2GgMzTo2F0v-tmONXkPU5qUuAZKDaj0_d6z6zMFQ_nenj0FmbRtpaF_C-ao_7VFdSqCEuPkiDeuTCSg4EK6PZF7iQ5hnuQSVsbAAzLJj_EaWcONGOk-EImSj5Dp_bHkVaXrEMX7FTH_t5qU71SCvNpmHPzQMdag1u9EBdUcMZ_s49pKobk-nNSIDTOUPxtOxUEcQ2XLyqvvweWjXnTXJPdNYa1JJb4P9xDtaS9GpAdQ6GMBItrqOwPCszLc84_GIAKKoEgHHRo1H0Df71PQAAAAGkAOGhAA"
    API_KEY = "7844051995:AAGY4U4XSAl7duM5SyaQS2VHecrpGsFQW7w"
    API_HASH = "e51a3154d2e0c45e5ed70251d68382de"
    API_ID = 15787995
    SUDO = 7046488481
    CHANNLS = ['Kali_Linux_BOTS']
    FORCE_SUBSCRIBE = True  # Default Force Subscribe Mode

# Ensure required directories and files exist
if not os.path.exists('./.session'):
    os.mkdir('./.session')

if not os.path.exists('./data.json'):
    json.dump({'users': [], 'languages': {}}, open('./data.json', 'w'), indent=3)

# Initialize Pyrogram Client
app = Client(
    "./.session/bot",
    bot_token=Config.API_KEY,
    api_hash=Config.API_HASH,
    api_id=Config.API_ID,
    parse_mode=enums.ParseMode.DEFAULT
)

@app.on_message(filters.private & filters.user(Config.SUDO) & filters.reply & filters.command("broadcast"))
async def broadcast_message(app: Client, message: types.Message):
    # Load users from MongoDB
    users = [user["user_id"] for user in users_collection.find()]

    if not users:
        await message.reply("No users available to broadcast.")
        return

    # The replied message to be broadcasted
    broadcast_content = message.reply_to_message

    # Counter to track successful and failed broadcasts
    success_count, fail_count = 0, 0

    # Broadcast the message to each user
    for index, user_id in enumerate(users):
        try:
            if broadcast_content.text:
                await app.send_message(chat_id=user_id, text=broadcast_content.text)
            elif broadcast_content.photo:
                await app.send_photo(chat_id=user_id, photo=broadcast_content.photo.file_id, caption=broadcast_content.caption or "")
            elif broadcast_content.video:
                await app.send_video(chat_id=user_id, video=broadcast_content.video.file_id, caption=broadcast_content.caption or "")
            elif broadcast_content.document:
                await app.send_document(chat_id=user_id, document=broadcast_content.document.file_id, caption=broadcast_content.caption or "")
            success_count += 1
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")
            fail_count += 1
            continue

        # Periodically update progress to the admin
        if (success_count + fail_count) % 10 == 0:
            await message.reply(f"Progress: {success_count + fail_count}/{len(users)} sent.")

    # Send a summary to the admin
    await message.reply(f"Broadcast completed.\nSuccess: {success_count}\nFailed: {fail_count}")

# Language Texts (No changes here)
LANGUAGE_TEXTS = {
    "en": {
        "welcome": "<b><i>Welcome to Face Swap Bot!</b></i> \n\n✈️ You can easily swap faces in your images with others 🔄.\n\n<b>⁀➴ Just simply send me two images to swap their faces</b> 🖇️🙂",
        "join_channel": "⚠️<b><i> To use this bot, you must first join our Telegram channel</i></b>\n\nAfter successfully joining, click the 🔐𝗝𝗼𝗶𝗻𝗲𝗱 button to confirm your bot membership and to continue",
        "verify_join": "🔐𝗝𝗼𝗶𝗻𝗲𝗱",
        "join_channel_btn": "Jᴏɪɴ ᴄʜᴀɴɴᴇʟ⚡️",
        "not_joined": "🤨 You are not a member of our channel. Please join and try again.",
        "downloading": "<b>Processing, please wait</b>...⏳🙃",
        "download_successful": "<b>Face Swap completed successfully</b> ✈️",
        "error": "✗ Sorry, there was an issue while processing 💔\nPlease check the images and try again ⚡"
    },
    "fa": {
        "welcome": "<b>به ربات تعویض چهره خوش آمدید!</b>\n\n✈️ شما می‌توانید به‌راحتی چهره‌ها را در تصاویر خود با یکدیگر تعویض کنید 🔄.\n\n<b>✦ کافیست دو تصویر را برای من ارسال کنید تا چهره‌های آن‌ها تعویض شود 🖇️🙂</b>",
        "join_channel": (
            "<b>⚠️ برای استفاده از این ربات، نخست شما باید به کانال‌ های زیر عضو گردید</b>.\n\n"
            "در غیر اینصورت این ربات برای شما کار نخواهد کرد. سپس روی دکمه | <b>عضـو شـدم 🔐 | </b>"
            "کلیک کنید تا عضویت ربات خود را تأیید کنید."
        ),
        "verify_join": "عضـو شـدم 🔐",
        "join_channel_btn": "عضـو کانال ⚡",
        "not_joined": "🤨 شما عضو کانال ما نیستید. لطفاً عضو شوید و دوباره امتحان کنید.",
        "downloading": "<b>در حال پردازش، لطفاً صبر کنید</b> ...⏳🙃",
        "download_successful": "<b>تعویض چهره با موفقیت انجام شد ✈️</b>",
        "error": "✗ متاسفانه مشکلی در پردازش پیش آمد 💔\nلطفا تصاویر را بررسی و دوباره تلاش نمایید⚡"
    }
}

# On Start and Language Selection
@app.on_message(filters.private & filters.regex('^/start$'))
async def ON_START_BOT(app: Client, message: types.Message):
    user_id = message.from_user.id
    user = users_collection.find_one({"user_id": user_id})

    if not user:
        # Insert new user into MongoDB
        users_collection.insert_one({
            "user_id": user_id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name
        })

        # Notify admin about new user
        await app.send_message(
            chat_id=Config.SUDO,
            text=f"↫︙New User Joined The Bot.\n\n  ↫ ID: ❲ {user_id} ❳\n  ↫ Username: ❲ @{message.from_user.username or 'None'} ❳\n  ↫ Firstname: ❲ {message.from_user.first_name} ❳\n\n↫︙Total Members: ❲ {users_collection.count_documents({})} ❳"
        )

    # Send language selection keyboard
    keyboard = [
        [types.InlineKeyboardButton("فارسـی 🇮🇷", callback_data="lang_fa"), types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    await message.reply("🇺🇸 <b>Select the language of your preference from below to continue</b>\n"
                        "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
                        "🇮🇷 <b>برای ادامه، لطفا نخست زبان مورد نظر خود را از گزینه زیر انتخاب کنید</b>", 
                        reply_markup=types.InlineKeyboardMarkup(keyboard))

# Handle Language Selection
@app.on_callback_query(filters.regex('^lang_'))
async def language_selection(app: Client, callback_query: types.CallbackQuery):
    language = callback_query.data.split('_')[1]
    user_id = str(callback_query.from_user.id)

    data = json.load(open('./data.json'))
    data['languages'][user_id] = language
    json.dump(data, open('./data.json', 'w'), indent=3)

    if Config.FORCE_SUBSCRIBE:
        join_message = LANGUAGE_TEXTS[language]["join_channel"].format(Config.CHANNLS[0])
        join_button = types.InlineKeyboardButton(LANGUAGE_TEXTS[language]["join_channel_btn"], url=f"https://t.me/{Config.CHANNLS[0]}")
        verify_button = types.InlineKeyboardButton(LANGUAGE_TEXTS[language]["verify_join"], callback_data="check_join")
        await callback_query.message.edit(
            text=join_message,
            reply_markup=types.InlineKeyboardMarkup([[join_button], [verify_button]])
        )
    else:
        await callback_query.message.edit(text=LANGUAGE_TEXTS[language]["welcome"])

# Check Join Method
async def CHECK_JOIN_MEMBER(user_id: int, channels: list, api_key: str):
    states = ['administrator', 'creator', 'member', 'restricted']
    for channel in channels:
        try:
            api_url = f"https://api.telegram.org/bot{api_key}/getChatMember?chat_id=@{channel}&user_id={user_id}"
            response = requests.get(api_url).json()
            if response.get('ok') and response['result']['status'] in states:
                continue
            else:
                return False, channel
        except Exception as e:
            print(f"Error checking membership: {e}")
            return False, channel
    return True, None

# Face Swap Method
def face_swap(image1, image2):
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

    img1 = cv2.imdecode(np.asarray(bytearray(image1), dtype=np.uint8), cv2.IMREAD_COLOR)
    img2 = cv2.imdecode(np.asarray(bytearray(image2), dtype=np.uint8), cv2.IMREAD_COLOR)

    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    faces1 = detector(gray1)
    faces2 = detector(gray2)

    if len(faces1) == 0 or len(faces2) == 0:
        return None

    landmarks1 = predictor(gray1, faces1[0])
    landmarks2 = predictor(gray2, faces2[0])

    # Swap face logic (simplified)
    img1 = np.array(img1)
    img2 = np.array(img2)
    swapped_img = np.copy(img2)

swapped_img[faces2[0].top():faces2[0].bottom(), faces2[0].left():faces2[0].right()] = img1[faces1[0].top():faces1[0].bottom(), faces1[0].left():faces1[0].right()]

    # Save the final swapped face image
    swapped_img_pil = Image.fromarray(swapped_img)
    byte_io = BytesIO()
    swapped_img_pil.save(byte_io, format='PNG')
    byte_io.seek(0)

    return byte_io

# Handling the face swap process in the bot
@app.on_message(filters.private & filters.photo)
async def on_receive_images(app: Client, message: types.Message):
    user_id = message.from_user.id
    data = json.load(open('./data.json'))

    if str(user_id) not in data['languages']:
        await message.reply("Please select your language first by using /start.")
        return

    language = data['languages'][str(user_id)]
    if len(message.photo) != 1:
        await message.reply(LANGUAGE_TEXTS[language]["error"])
        return

    file_id = message.photo.file_id
    file_info = await app.get_file(file_id)
    file_path = file_info.file_path

    # Download the image
    img_response = await app.download_media(file_id)
    user_images_path = f"./user_images/{user_id}/"

    if not os.path.exists(user_images_path):
        os.makedirs(user_images_path)

    img_path = os.path.join(user_images_path, f"image1.png")
    os.rename(img_response, img_path)

    await message.reply(LANGUAGE_TEXTS[language]["downloading"])

    # Wait for second image from user
    second_image_message = await app.listen(user_id)

    if len(second_image_message.photo) != 1:
        await message.reply(LANGUAGE_TEXTS[language]["error"])
        return

    file_id_2 = second_image_message.photo.file_id
    file_info_2 = await app.get_file(file_id_2)
    file_path_2 = file_info_2.file_path

    # Download the second image
    img_response_2 = await app.download_media(file_id_2)
    img_path_2 = os.path.join(user_images_path, f"image2.png")
    os.rename(img_response_2, img_path_2)

    # Perform face swap
    try:
        with open(img_path, 'rb') as img1, open(img_path_2, 'rb') as img2:
            swapped_img = face_swap(img1.read(), img2.read())

        if swapped_img:
            await app.send_photo(user_id, photo=swapped_img, caption=LANGUAGE_TEXTS[language]["download_successful"])
        else:
            await message.reply(LANGUAGE_TEXTS[language]["error"])
    except Exception as e:
        print(f"Error during face swap: {e}")
        await message.reply(LANGUAGE_TEXTS[language]["error"])

# Subscription Check for New Users
@app.on_message(filters.private & filters.command("checkjoin"))
async def check_joined(app: Client, message: types.Message):
    user_id = message.from_user.id
    if Config.FORCE_SUBSCRIBE:
        is_joined, channel = await CHECK_JOIN_MEMBER(user_id, Config.CHANNLS, Config.API_KEY)
        if not is_joined:
            await message.reply(f"⚠️ You are not a member of the required channel: @{channel}. Please join the channel to continue.")
            return
        else:
            await message.reply(LANGUAGE_TEXTS["en"]["welcome"])
    else:
        await message.reply(LANGUAGE_TEXTS["en"]["welcome"])

# Start the bot
app.run()
