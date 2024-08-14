import uuid
import requests
import re
import datetime
import pytz
import os
import pandas as pd
import html_text
import time
from prompts import create_combined_prompt
from gpt_classifier import gpt_html_extract
from decouple import config
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
CSV_HEADERS = [
    'TIME_SCRAPED_PST', 'PRODUCT_TYPE', 'URL', 'TITLE', 'PRICE', 'RATING', 'NO_OF_REVIEWS',
    'OPERATING_SYSTEM', 'PROCESSOR_BRAND', 'PROCESSOR_FAMILY', 'PROCESSOR_GENERATION',
    'CPU_SPEED', 'GRAPHICS_BRAND', 'GRAPHICS_FAMILY', 'GRAPHICS_RAM', 'GRAPHICS_RAM_TYPE',
    'RAM_MEMORY', 'RAM_TYPE', 'RAM_SPEED', 'STORAGE_SIZE', 'STORAGE_TYPE', 'STORAGE_OTHERS',
    'DISPLAY_SIZE', 'DISPLAY_RESOLUTION', 'DISPLAY_REFRESH_RATE', 'DISPLAY_OTHERS', "HASH_ID", "COSMOS_DB"
]
CWD = config("CWD")
OUTPUT_CSV_FOLDER = config("OUTPUT_CSV_FOLDER")
OUTPUT_CSV_NAME = config("OUTPUT_CSV_NAME")
CSV_FILE_PATH = f"{OUTPUT_CSV_FOLDER}/{OUTPUT_CSV_NAME}"
PRODUCT_TYPES = ['laptop', 'desktop']
REQUEST_HEADERS = {
    "Accept": "*/*",
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}
MAX_RETRIES = 3
TIME_ZONE = 'America/Los_Angeles'
PAGE_SIZE = 40
TEST_LIMIT = 1  # Limit for testing purposes
REQUEST_DELAY = 3  # Delay between requests
TEST_MODE = False

# Ensure output directory exists
if not os.path.exists(OUTPUT_CSV_FOLDER):
    os.mkdir(OUTPUT_CSV_FOLDER)

# Function to remove extra spaces from a string
def remove_extra_space(item):
    if item:
        return re.sub(' +', ' ', item).strip()
    return item

# Function to check if the CSV file exists and handle accordingly
def read_csv_file():
    if os.path.isfile(CSV_FILE_PATH):
        return pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")
    else:
        df_only_headers = pd.DataFrame(columns=CSV_HEADERS)
        df_only_headers.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
        return df_only_headers
    
# Function to perform a request with retries
def request_with_retries(url):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = requests.get(url, headers=REQUEST_HEADERS)
            if response.status_code != 200:
                logging.warning(f"Received status code {response.status_code}. Retrying ({retry_count + 1}/{MAX_RETRIES})...")
                time.sleep(REQUEST_DELAY)
                retry_count += 1
            else:
                return response
        except Exception as e:
            logging.warning(f"Request failed: {e}. Retrying ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(REQUEST_DELAY)
            retry_count += 1
    logging.error(f"Failed to retrieve URL after {MAX_RETRIES} attempts.")
    return None

# Function to perform GPT extraction with retries
def gpt_extraction_with_retries(text, prompt):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        result = gpt_html_extract(text, prompt)
        if result:
            return result
        logging.warning(f"Retrying after delay ({retry_count + 1}/{MAX_RETRIES})...")
        time.sleep(REQUEST_DELAY)
        retry_count += 1
    
    logging.error(f"Failed GPT extraction after {MAX_RETRIES} attempts.")
    return None

# Function to parse and process a single product
def parse_product(product, product_type, product_num):

    product_url = "https://www.lenovo.com/us/en" + product['url']

    current_time = datetime.datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%dT%H:%M:%S.%f")
    hash_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3] + str(uuid.uuid4().hex)[:15]
    basic_dict = {
        "HASH_ID": hash_id, 
        "TIME_SCRAPED_PST": current_time,
        'PRODUCT_TYPE': product_type,
        "URL": product_url,
        'TITLE': product.get('summary', ''),
        "PRICE": product.get('currencySymbol', ' ') + product.get('finalPrice', ''),
        'RATING': product.get('ratingStar', ''),
        'NO_OF_REVIEWS': product.get('commentCount', ''),
        "COSMOS_DB": "N"
    }

    product_specs = product.get('classification', [])
    combined_text = ""
    valid_spec_titles = {"processor", "graphic", "display", "memory", "storage"}
    specs_dict = {}
    for spec in product_specs:
        spec_title = spec['a'].lower()
        spec_value = html_text.extract_text(spec['b']).encode('ascii', 'ignore').decode()
        if any(valid_word in spec_title for valid_word in valid_spec_titles):
            combined_text += f"{spec_title}: {spec_value}\n"
        else:
            specs_dict[remove_extra_space(spec_title).upper().replace(" ", "_")] = spec_value

    prompt = create_combined_prompt()  # Updated to match the prompt creation
    time.sleep(REQUEST_DELAY)  # Delay between GPT requests
    spec_details = gpt_extraction_with_retries(combined_text, prompt)
    if spec_details:
        spec_details = json.loads(spec_details)
        spec_details.update(basic_dict)
        spec_details.update(specs_dict)
        for key, value in spec_details.items():
            if value == 'None':
                spec_details[key] = ''
        return spec_details

    return None

# Main scraping function
def get_products(product_type):
    logging.info(f"Extracting {product_type}")
    if product_type == "laptop":
        page_filter_id = "3291392e-85e3-4a03-89c2-a6b2b308d441"
    elif product_type == "desktop":
        page_filter_id = "1415809c-92fa-4b2a-bcca-31a567e76a93"

    url = f'https://openapi.lenovo.com/us/en/ofp/search/dlp/product/query/get/_tsc?pageFilterId="{page_filter_id}"&params={{"classificationGroupIds":"400001","pageFilterId":"","facets":[{{"facetId":"711","selectedValues":"Pre-Built Models"}}],"page":1,"pageSize":{PAGE_SIZE}}}'
    url = re.sub('"pageFilterId":""', f'"pageFilterId":"{page_filter_id}"', url)
    url = re.sub('pageFilterId=""', f'pageFilterId={page_filter_id}', url)
    
    r = request_with_retries(url)
    if r is None:
        logging.error(f"Failed to retrieve products for product_type: {product_type}")
        return
    
    try:
        page_count = r.json()['data']['pageCount']
    except Exception as e:
        logging.error(f"Error extracting page count: {e}")
        return
    
    csv_file = read_csv_file()
    product_url_list = csv_file['URL'].tolist()
    
    processed_count = 0

    for i in range(1, page_count + 1):
        page_url = re.sub(r'"page":(\d+)', f'"page":{i}', url)
        r = request_with_retries(page_url)
        if r is None:
            continue
        try:
            products = r.json()['data']['data']
        except Exception as e:
            logging.error(f"Error extracting products: {e}")
            continue
        

        for idx, product in enumerate(products):
            if 'url' not in product:
                logging.error(f"Missing 'url' for product number {idx + 1}")
                continue
            
            product_full_url = "https://www.lenovo.com/us/en" + product['url']
            if product_full_url not in product_url_list:
                try:
                    result = parse_product(product, product_type, idx)
                    if result:
                        print(result)
                        df_product_details = pd.DataFrame([result])
                        print(df_product_details)
                        csv_file = pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")
                        merge = pd.concat([csv_file, df_product_details], ignore_index=True)
                        merge.sort_values(by='TIME_SCRAPED_PST', ascending=False).to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
                        processed_count += 1
                        logging.info(f"Processed product number {processed_count}: {product['url']}")
                        if TEST_MODE and processed_count == TEST_LIMIT:
                            return
                except Exception as e:
                    logging.error(f"Error processing product number {processed_count + 1}: {product['url']} - {e}")
            else:
                logging.info('product already exists')

# Main script execution
if __name__ == "__main__":
    # Get the current working directory
    current_dir = os.getcwd()

    # Extract the actual directory name from the current path
    current_dir_name = os.path.basename(current_dir)

    # Check if the current directory name matches the expected name
    if current_dir_name != CWD:
        print(f"Incorrect working directory. Please cd into {CWD}")
    else:
        logging.info("Starting lenovo.com scraper")
        for product_type in PRODUCT_TYPES:
            get_products(product_type)
        logging.info("Done! All PRODUCT_TYPES processed.")
