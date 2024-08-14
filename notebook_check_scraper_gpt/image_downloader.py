import datetime
import requests
from io import BytesIO
from PIL import Image
import time
import concurrent.futures
import os
import traceback

def download_and_process_images(images, hash_id):
    start_time = time.time()
    internal_found = []

    def download_and_process_image(image, session):
        if image['TYPE'] == 'internal':
            response = session.get(f"{image['HREF']}")
            if response.status_code == 200:
                image_bytes = response.content
                image_name = "infer_img_" + image['HREF'].split("/")[-1]
                internal_found.append(image_name)
                if is_image_large_enough(image_bytes, 200, 200):
                    save_image_to_disk(image_bytes, hash_id, image_name)
                    return (image_name, image['TITLE'])
            print(f"Failed to download or process image from URL: {image['HREF']}, {response.status_code}")
            return None
        else:
            if len(internal_found) == 0:
                response = session.get(f"{image['HREF']}")
                if response.status_code == 200:
                    image_bytes = response.content
                    image_name = image['HREF'].split("/")[-1]
                    if is_image_large_enough(image_bytes, 200, 200):
                        save_image_to_disk(image_bytes, hash_id, image_name)
                        return (image_name, image['TITLE'])

    def is_image_large_enough(image_bytes, min_width, min_height):
        try:
            image = Image.open(BytesIO(image_bytes))
            width, height = image.size
            return width > min_width and height > min_height
        except:
            return None

    def save_image_to_disk(image_bytes, hash_id, image_name):
        folder_path = os.path.join('images', hash_id)
        os.makedirs(folder_path, exist_ok=True)
        image_path = os.path.join(folder_path, image_name)
        with open(image_path, 'wb') as image_file:
            image_file.write(image_bytes)

    # Download and process images concurrently
    try:
        with requests.Session() as session:
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                results = list(executor.map(download_and_process_image, images, [session] * len(images)))

        valid_results = [result for result in results if result is not None]
        if valid_results:
            print(f"Added images for {hash_id}")
            return True
    except Exception as e:
        print(f"Error processing images for {hash_id}, {e}, {traceback.format_exc()}")
        return False

    end_time = time.time()
    print(f"Images time taken {round(end_time - start_time, 2)} seconds")
