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
import json
import logging
from decouple import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
CSV_HEADERS = [
    'TIME_SCRAPED_PST', 'PRODUCT_TYPE', 'URL', 'TITLE', 'RATING', 'NO_OF_REVIEWS',
    'OPERATING_SYSTEM', 'PROCESSOR_BRAND', 'PROCESSOR_FAMILY', 'PROCESSOR_GENERATION',
    'CPU_SPEED', 'GRAPHICS_BRAND', 'GRAPHICS_FAMILY', 'GRAPHICS_RAM', 'GRAPHICS_RAM_TYPE',
    'RAM_MEMORY', 'RAM_TYPE', 'RAM_SPEED', 'STORAGE_SIZE', 'STORAGE_TYPE', 'STORAGE_OTHERS',
    'DISPLAY_SIZE', 'DISPLAY_RESOLUTION', 'DISPLAY_REFRESH_RATE', 'DISPLAY_OTHERS', 'DISCLAIMER_POINTS', "HASH_ID", "COSMOS_DB"
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
PAGE_SIZE = 100000
TEST_LIMIT = 10  # Limit for testing purposes
REQUEST_DELAY = 3  # Delay between requests
TEST_MODE = False

# Ensure output directory exists
if not os.path.exists(OUTPUT_CSV_FOLDER):
    os.mkdir(OUTPUT_CSV_FOLDER)

# Function to check if the CSV file exists and handle accordingly
def read_csv_file():
    if os.path.isfile(CSV_FILE_PATH):
        return pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")
    else:
        df_only_headers = pd.DataFrame(columns=CSV_HEADERS)
        df_only_headers.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
        return df_only_headers

# Function to remove extra spaces from a string
def remove_extra_space(item):
    if item:
        return re.sub(' +', ' ', item).strip()
    return item

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
            logging.info(f"GPT Response received.")
            return result
        logging.warning(f"Retrying GPT after delay ({retry_count + 1}/{MAX_RETRIES})...")
        time.sleep(REQUEST_DELAY)
        retry_count += 1
    
    logging.error(f"Failed GPT extraction after {MAX_RETRIES} attempts.")
    return None

# Function to parse and process a single product
def parse_product(product, product_type, product_num):
    product_url = product['ctaViewDetailsLink']
    product_details_url = "pdp%2F" + (product_url.split("pdp/")[1])
    url = f'https://www.hp.com/us-en/shop/app/api/web/graphql/page/{product_details_url}/async'
    footer_links_url = f'https://www.hp.com/us-en/shop/app/api/web/graphql/page/{product_details_url}/footerLinks'
    
    r = request_with_retries(url)
    r2 = request_with_retries(footer_links_url)
    
    if r is None or r2 is None:
        logging.error(f"Couldn't extract data for product number {product_num}: {product_url}")
        return None
    
    try:
        product_specs = r.json()['data']['page']['pageComponents']['pdpTechSpecs']['technical_specifications']
    except Exception as e:
        logging.error(f"Error extracting product_specs for product number {product_num}: {product_url} - {e}")
        product_specs = []

    try:
        footer_specs = r2.json()['data']['page']['pageComponents']['pdpFootnotesDisclaimer']
    except Exception as e:
        logging.error(f"Error extracting footer_specs for product number {product_num}: {product_url} - {e}")
        footer_specs = []

    disclaimer_list = []
    if footer_specs:
        try:
            footer_specs_elements = [element for element in footer_specs if element['section'] == 'SPECS']
            if footer_specs_elements:
                disclaimer_points = footer_specs_elements[0]['disclaimerPoints']
                for point in disclaimer_points:
                    item = html_text.extract_text(point).encode('ascii', 'ignore').decode()
                    disclaimer_list.append(item)
        except Exception as e:
            logging.error(f"Error processing footer_specs for product number {product_num}: {product_url} - {e}")
            disclaimer_list = []

    current_time = datetime.datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%dT%H:%M:%S.%f")
    hash_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3] + str(uuid.uuid4().hex)[:15]
    basic_dict = {
        "HASH_ID": hash_id,
        "TIME_SCRAPED_PST": current_time,
        'PRODUCT_TYPE': product_type,
        "URL": product_url,
        'TITLE': product.get('name', ''),
        'RATING': product.get('rating', ''),
        'NO_OF_REVIEWS': product.get('numReviews', ''),
        "COSMOS_DB": "N"
    }
    
    combined_text_for_gpt = ""
    specs_dict = {}
    valid_spec_titles = {"processor", "graphics", "graphic card", "display", "memory", "storage", "hard drive", "internal drive", "weight"}
    for spec in product_specs:
        spec_title = spec['name'].lower()
        spec_value = html_text.extract_text((spec['value'][0])['value'][0]).encode("ascii", "ignore").decode()
        if any(valid_word in spec_title for valid_word in valid_spec_titles):
            combined_text_for_gpt += f"{spec_title}: {spec_value}\n"
        else:
            specs_dict[spec_title.upper().replace(" ", "_")] = spec_value

    prompt = create_combined_prompt()  # Updated to match the prompt creation

    spec_details = gpt_extraction_with_retries(combined_text_for_gpt, prompt)
    if spec_details:
        spec_details = json.loads(spec_details)
        spec_details.update(basic_dict)
        spec_details.update(specs_dict)
        spec_details['DISCLAIMER_POINTS'] = " ".join(disclaimer_list)
        for key, value in spec_details.items():
            if value == 'None':
                spec_details[key] = ''
        return spec_details
    

    return None

# Main scraping function
def get_products(product_type):
    logging.info(f"Extracting {product_type}")
    url = f'https://www.hp.com/wcs/resources/store/10151/component/vwa/finder-results?path=vwa%2F{product_type}s%2Fordr%3DBuild-to-Order,Ready-to-Ship&beginIndex=0&pageSize={PAGE_SIZE}'
    
    r = request_with_retries(url)
    if r is None:
        logging.error(f"Failed to retrieve products for product_type: {product_type}")
        return
    
    try:
        products = r.json()['vwaDetails']['products']
    except Exception as e:
        logging.error(f"Error extracting products: {e}")
        return
    
    csv_file = read_csv_file()
    product_url_list = csv_file['URL'].tolist()
    
    processed_count = 0

    for idx, product in enumerate(products):
        if product['ctaViewDetailsLink'] not in product_url_list:
            try:
                result = parse_product(product, product_type, idx)
                if result:
                    df_product_details = pd.DataFrame([result])
                    csv_file = pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")
                    merge = pd.concat([csv_file, df_product_details], ignore_index=True)
                    merge.sort_values(by='TIME_SCRAPED_PST', ascending=False).to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
                    processed_count += 1
                    logging.info(f"Processed product number {processed_count}: {product['ctaViewDetailsLink']}")
                    if TEST_MODE and processed_count == TEST_LIMIT:
                        return
            except Exception as e:
                logging.error(f"Error processing product number {processed_count + 1}: {product['ctaViewDetailsLink']} - {e}")
        else:
            logging.info('Product already exists')

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
        logging.info("Starting hp.com scraper")
        for product_type in PRODUCT_TYPES:
            get_products(product_type)
        logging.info("Done! All PRODUCT_TYPES processed.")
