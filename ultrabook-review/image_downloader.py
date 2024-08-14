import datetime
import os
import pandas as pd
import requests
import csv
from io import BytesIO
from PIL import Image
import time
import concurrent.futures
# import database_api
from ultrabook_utils import get_hash_id
import traceback
from fake_useragent import UserAgent
ua = UserAgent()

def download_and_process_images(images, section_hash_id):
    def download_and_process_image(image_url, session):
        image_name = image_url.split("/")[-1]
        headers = {'User-Agent': ua.random}
        response = session.get(image_url, headers=headers)
        if response.status_code == 200:
            image_bytes = response.content
            if is_image_large_enough(image_bytes, 200, 200):
                print(f"image ok: {image_url}")   
                hex_data = image_bytes.hex()
                size_kb = len(image_bytes)/1024
                hash_id = get_hash_id()
                cur_time = datetime.datetime.now()
                return {'HASH_ID': hash_id, 'IMAGE_URL': image_url, 'FILE_DATA': hex_data, 'FILE_NAME': image_name, 
                        'FILE_SIZE': size_kb, 'UPLOAD_TIME': cur_time, 'PARENT_HASH_ID': section_hash_id}
        print(f"Failed to download or process image from URL: {image_url}, {response.status_code}")
        return None
        

    def is_image_large_enough(image_bytes, min_width, min_height):
        try:
            image = Image.open(BytesIO(image_bytes))
            width, height = image.size
            return width > min_width and height > min_height
        except:
            return None

    # Download and process images concurrently
    try:
        MAX_WORKERS = 50
        results = None
        with requests.Session() as session:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                results = list(executor.map(download_and_process_image, images, [session]*len(images)))

        valid_results = [result for result in results if result is not None]

        if valid_results:
            return valid_results
        else:
            return None
    except Exception as e:
        print(f"Error processing images for {section_hash_id}, {e}, {traceback.format_exc()}")
        return None

