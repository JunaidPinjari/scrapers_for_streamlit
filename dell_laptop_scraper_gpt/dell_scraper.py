import logging
import math
import os
import uuid
import requests
import time
import pandas as pd
import datetime
import pytz
from lxml import html
import re
import json
from prompts import create_combined_prompt
from gpt_classifier import gpt_html_extract
from decouple import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
CSV_HEADERS = [
    'TIME_SCRAPED_PST', 'PRODUCT_TYPE', 'PRODUCT_ID', 'URL', 'TITLE', 'PRICE', 'RATING', 'NO_OF_REVIEWS',
    "HEIGHT", "WIDTH", "DEPTH", "WEIGHT_KG",'PROCESSOR_BRAND', 'PROCESSOR_FAMILY', 'PROCESSOR_GENERATION', 'CPU_CACHE',
    'CPU_CORES', 'CPU_THREADS', 'CPU_SPEED', 'GRAPHICS_BRAND', 'GRAPHICS_FAMILY', 'GRAPHICS_RAM',
    'GRAPHICS_RAM_TYPE', 'RAM_MEMORY', 'RAM_TYPE', 'RAM_SPEED', 'STORAGE_SIZE', 'STORAGE_TYPE',
    'STORAGE_OTHERS', 'DISPLAY_SIZE', 'DISPLAY_RESOLUTION', 'DISPLAY_REFRESH_RATE', 'DISPLAY_OTHERS', 
    "WIRELESS", "POWER", 'PORTS', 'SLOTS', "CHASSIS", "CASE", "KEYBOARD", "TOUCHPAD", 
    "CAMERA", "PALMREST", "OPTICAL_DRIVE", 'OPERATING_SYSTEM', "HASH_ID", "COSMOS_DB"
]
CWD = config("CWD")
OUTPUT_CSV_FOLDER = config("OUTPUT_CSV_FOLDER")
OUTPUT_CSV_NAME = config("OUTPUT_CSV_NAME")
CSV_FILE_PATH = f"{OUTPUT_CSV_FOLDER}/{OUTPUT_CSV_NAME}"
PRODUCT_TYPES = ['laptop', 'desktop']
MAX_RETRIES = 3
TIME_ZONE = 'America/Los_Angeles'
REQUEST_DELAY = 3  # Delay between requests in seconds
TEST_MODE = False  # Set this to True to enable test mode
TEST_LIMIT = 5 # Limit the number of products to process in test mode

# Ensure output directory exists
if not os.path.exists(OUTPUT_CSV_FOLDER):
    os.mkdir(OUTPUT_CSV_FOLDER)

def retry_request(url):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response
            logging.warning(f"Received status code {response.status_code}. Retrying ({retry_count + 1}/{MAX_RETRIES})...")
        except Exception as e:
            logging.warning(f"Request failed: {e}. Retrying ({retry_count + 1}/{MAX_RETRIES})...")
        time.sleep(REQUEST_DELAY)
        retry_count += 1
    logging.error(f"Failed to retrieve URL after {MAX_RETRIES} attempts.")
    return None

def gpt_extraction_with_retries(text, prompt):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            result = gpt_html_extract(text, prompt)
            if result:
                return result
        except Exception as e:
            logging.warning(f"GPT extraction failed: {e}. Retrying ({retry_count + 1}/{MAX_RETRIES})...")
        time.sleep(REQUEST_DELAY)
        retry_count += 1
    logging.error(f"Failed GPT extraction after {MAX_RETRIES} attempts.")
    return None

def total_pages(url):
    try:
        response = retry_request(url)
        if response:
            tree = html.fromstring(response.content)
            total_results_text = tree.xpath('//*[@class="resultcount"]/text()')
            total_results = int(total_results_text[0].replace(',', '')) if total_results_text else 0
            return math.ceil(total_results / 12)
    except Exception as e:
        logging.error(f"Error calculating total pages: {e}")
    return 0

def parse_product_page(url, product_id, product_type):
    try:
        response = retry_request(url)
        if response:
            tree = html.fromstring(response.content)
            script_tag = tree.xpath('//script[contains(text(), "offers")]/text()')
            if script_tag:
                json_data = json.loads(script_tag[0])
                parsed_data = parse_product_details(tree, json_data, product_id, url, product_type)
                if parsed_data:
                    save_to_csv(parsed_data)
                    logging.info(f'Processed product: ID: {product_id}, URL: {url}')
    except Exception as e:
        logging.error(f"Error parsing product page: {e}")

def parse_search_results(url, product_type):
    processed_ids = []
    if os.path.isfile(CSV_FILE_PATH):
        df = pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")
        processed_ids = df['PRODUCT_ID'].tolist()

    try:
        processed_count = 0
        response = retry_request(url)
        if response:
            tree = html.fromstring(response.content)
            products = tree.xpath('//*[@id="ps-wrapper"]/article')
            for product in products:
                if TEST_MODE and processed_count == TEST_LIMIT:
                    logging.info(f"Test limit reached for {product_type}, stopping further processing.")
                    return False
                try:
                    product_id = product.xpath('./@data-product-id')[0]
                    product_url = "https:" + product.xpath('./section[2]/div[1]/h3/a/@href')[0]
                    if product_id not in processed_ids:
                        parse_product_page(product_url, product_id, product_type)
                        processed_count += 1
                        processed_ids.append(product_id)  # Add processed product ID to the list
                except IndexError as e:
                    logging.error(f"Product parsing error: {e}")
            return True
    except Exception as e:
        logging.error(f"Error parsing search results: {e}")
        return False
    
def parse_product_details(tree, json_data, product_id, url, product_type):
    def get_text(item, index):
        return item[index] if item and len(item) > index else ""

    def clean_text(item):
        return re.sub(' +', ' ', item).strip().lower() if item else item

    try:
        title = json_data.get("name", "")
        ratings = get_text(tree.xpath('//*[@id="main-content-container"]/div[1]/div[1]/div[1]/div[2]/a[1]/text()'), 1)
        rating_stars = f"{json_data['aggregateRating']['ratingValue']} out of 5.0" if "aggregateRating" in json_data else ""
        num_of_reviews = json_data.get("aggregateRating", {}).get("ratingCount", get_text(ratings.split(), 1).strip("()") if ratings else "")
        price = f"$ {json_data['offers']['price']}" if "offers" in json_data else ""

        specs_dict = {}
        current_time = datetime.datetime.now(pytz.timezone(TIME_ZONE)).strftime("%Y-%m-%dT%H:%M:%S.%f")
        hash_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3] + str(uuid.uuid4().hex)[:15]
        basic_dict = {
            "HASH_ID": hash_id, "TIME_SCRAPED_PST": current_time, "PRODUCT_TYPE": product_type, 'PRODUCT_ID': product_id, "URL": url, 
            'TITLE': title, 'PRICE': price, 'RATING': rating_stars, 'NO_OF_REVIEWS': num_of_reviews, "COSMOS_DB": "N"
        }

        combined_text = ""
        valid_spec_titles = {"processor", "graphics card", "display", "memory", "hard drive", "storage", "dimension", "weight"}

        specs_one = tree.xpath('//*[@id="tech-spec-container"]/div/ul/li')
        if specs_one is not None:
            for spec in specs_one:
                spec_title = clean_text(get_text(spec.xpath("./div/text()"), 0))
                spec_value_list = spec.xpath("./p/text() | ./p/strong/following-sibling::text() | ./p/span/text()")
                spec_value = ', '.join(spec_value_list).replace("®", "").replace("™", "")
                if any(valid_word in spec_title.lower() for valid_word in valid_spec_titles):
                    combined_text += f"{spec_title}: {spec_value}\n"
                else:
                    specs_dict[clean_text(spec_title).upper().replace(" ", "_")] = spec_value
        else:
            specs_one = tree.xpath('//*[@id="techspecs_section"]//div[contains(@class, "ux-module-row-wrap")]')
            if specs_one is not None:
                specs_one = specs_one[0]
                spec_divs = specs_one.xpath('./div')
                for spec in spec_divs:
                    title_list = spec.xpath('.//h2/text()')
                    value_list = spec.xpath('.//div[contains(@class, "ux-readonly-title") or contains(@class, "ux-cell-title")]/text()')
                    if title_list and value_list:
                        spec_title = clean_text(title_list[0])
                        spec_value = clean_text(value_list[0])
                        if any(valid_word in spec_title.lower() for valid_word in valid_spec_titles):
                            combined_text += f"{spec_title}: {spec_value}\n"
                        else:
                            specs_dict[clean_text(spec_title).upper().replace(" ", "_")] = spec_value
                    else:
                        pass
            else:
                specs_one = tree.xpath('//div[@id="ps-wrapper" and contains(@class, "dell-ps") and contains(@class, "ps")]')[0]
                if specs_one is not None:
                    article = specs_one.xpath('.//article')[0]
                    section = article.xpath('.//section')[1]
                    divs = section.xpath('./div[1]/ul/li')
                    for div in divs:
                        title_list = div.xpath('.//h4/text()')
                        value_list = div.xpath('.//div[contains(@class, "ps-specs-item")]/text()')
                        if title_list and value_list:
                            spec_title = clean_text(title_list[0])
                            spec_value = clean_text(value_list[0])
                            if any(valid_word in spec_title.lower() for valid_word in valid_spec_titles):
                                combined_text += f"{spec_title}: {spec_value}\n"
                            else:
                                specs_dict[clean_text(spec_title).upper().replace(" ", "_")] = spec_value
                        else:
                            pass
                else:
                    print('No section with class "techspecs_section" found')

        prompt = create_combined_prompt()
        spec_details = gpt_extraction_with_retries(combined_text, prompt)
        if spec_details:
            spec_details = json.loads(spec_details)
            spec_details.update(basic_dict)
            spec_details.update(specs_dict)
            for key, value in spec_details.items():
                if value == 'None':
                    spec_details[key] = ''
            return spec_details
    except Exception as e:
        logging.error(f"Error parsing product details: {e} for product {url}")
    return None

def save_to_csv(parsed_data):
    try:
        if os.path.isfile(CSV_FILE_PATH):
            df = pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")
        else:
            df = pd.DataFrame(columns=CSV_HEADERS)
        df = pd.concat([df, pd.DataFrame([parsed_data])], ignore_index=True)
        df.sort_values(by='TIME_SCRAPED_PST', ascending=False).to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")

def scrape_dell(product_type):
    url = f'https://www.dell.com/en-us/shop/{product_type}-computers/scr/{product_type}s'
    total_pages_count = total_pages(url)
    logging.info(f"Total pages for {product_type}: {total_pages_count}")
    
    for i in range(1, total_pages_count + 1):
        next_page_url = f"{url}?page={i}"
        logging.info(f"Processing page {i} for {product_type}")
        func_output = parse_search_results(next_page_url, product_type)
        if not func_output:
            break
        time.sleep(REQUEST_DELAY)
        
if __name__ == "__main__":
    # Get the current working directory
    current_dir = os.getcwd()

    # Extract the actual directory name from the current path
    current_dir_name = os.path.basename(current_dir)

    # Check if the current directory name matches the expected name
    if current_dir_name != CWD:
        print(f"Incorrect working directory. Please cd into {CWD}")
    else:
        logging.info("Starting dell.com scraper")
        for product_type in PRODUCT_TYPES:
            scrape_dell(product_type)
        logging.info("Done! All PRODUCT_TYPES processed.")
