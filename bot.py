import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# Replace these with your own values
API_ID = '15787995'
API_HASH = 'e51a3154d2e0c45e5ed70251d68382de'
BOT_TOKEN = '7844051995:AAHTkN2eJswu-CAfe74amMUGok_jaMK0hXQ'

# Initialize the Pyrogram Client
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
def start(client, message: Message):
    message.reply_text("Hello! Send me a prompt and I will generate an image for you.")

@app.on_message(filters.text & filters.private)
def generate_image(client, message: Message):
    prompt = message.text
    url = f"https://for-free.serv00.net/imgen.php?prompt={prompt.replace(' ', '+')}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open("generated_image.jpg", "wb") as file:
                file.write(response.content)
            message.reply_photo("generated_image.jpg")
            os.remove("generated_image.jpg")
        else:
            message.reply_text("Failed to generate image. Please try again later.")
    except Exception as e:
        message.reply_text(f"An error occurred: {e}")

# Run the bot
app.run()
