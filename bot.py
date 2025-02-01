import aiohttp
import asyncio
from gradio_client import Client, file
import aiofiles

# Gradio Client setup
client = Client("CharlieAmalet/Tools3ox_Background-Motion-Blur_Api")

# Catbox API URL
CATBOX_URL = "https://catbox.moe/user/api.php"

async def upload_to_catbox(file_path):
    """Upload the file to Catbox and return the URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(file_path, "rb") as f:
                response = await session.post(
                    CATBOX_URL,
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": await f.read()},
                )
                response.raise_for_status()
                return (await response.text()).strip()
    except Exception as e:
        print(f"Failed to upload file to Catbox: {e}")
        return None

async def process_image(image_url, distance_blur=200, amount_blur=1):
    """Process the image by applying motion blur and return the result filepath."""
    try:
        result = client.predict(
            img=file(image_url),  # URL of the image to process
            distance_blur=distance_blur,
            amount_blur=amount_blur,
            api_name="/blur"
        )
        
        # Debugging: Print the result type and content
        print(f"Result type: {type(result)}")
        print(f"Result content: {result}")

        # If the result is a list, we need to access the first item or use the appropriate key
        if isinstance(result, list):
            result = result[0]  # Assuming the result is a list, access the first item
        
        # Check if the result is a dictionary
        if isinstance(result, dict) and "filepath" in result:
            return result["filepath"]
        else:
            print("Unexpected result format: ", result)
            return None

    except Exception as e:
        print(f"Error processing image: {e}")
        return None

async def main(image_url):
    """Main function to process image and upload result."""
    # Apply motion blur and get result file path
    result_filepath = await process_image(image_url)
    if result_filepath:
        # Upload the resulting image to Catbox
        result_url = await upload_to_catbox(result_filepath)
        if result_url:
            print(f"Image processed and uploaded! Here is the URL: {result_url}")
        else:
            print("Failed to upload the image to Catbox.")
    else:
        print("Failed to process the image.")

# Replace with the image URL you want to process
image_url = "https://i.imghippo.com/files/eNXe4934iU.jpg"  # Example image URL

# Run the script
if __name__ == "__main__":
    asyncio.run(main(image_url))
