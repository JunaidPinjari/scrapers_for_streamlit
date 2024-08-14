import os
import warnings
import requests
from bs4 import BeautifulSoup
import datetime
import time
import uuid
import html_text
import pandas as pd
from decouple import config

warnings.simplefilter(action='ignore', category=FutureWarning)

CWD = config("CWD")
OUTPUT_CSV_FOLDER = config("OUTPUT_CSV_FOLDER")
OUTPUT_CSV_NAME = config("OUTPUT_CSV_NAME")
CSV_FILE_PATH = f"{OUTPUT_CSV_FOLDER}/{OUTPUT_CSV_NAME}"
CSV_HEADERS = [
    "URL", "TITLE", "PRODUCT", "BRAND",
    "COMMENTS", "REVIEW", "OPERATING_SYSTEM_STRING", "MAINBOARD_STRING",
    "PRICE_USD", "PRICE_STRING", "PUBLISHED_DATE", "PUBLISHED_DATE_STRING",
    "SCRAPED_TIME", "PROCESSOR", "PROCESSOR_PL1", "PROCESSOR_PL2",
    "PROCESSOR_STRING", "GRAPHICS_ADAPTER", "GRAPHICS_ADAPTER_TDP",
    "GRAPHICS_ADAPTER_STRING", "BATTERY_TECHNOLOGY", "BATTERY_TYPE",
    "BATTERY_WH", "BATTERY_MAH", "BATTERY_PARALLEL", "BATTERY_SERIES",
    "BATTERY_STRING", "BATTERY_H264", "BATTERY_IDLE", "BATTERY_LOAD",
    "BATTERY_WIFI", "WIFI", "BLUETOOTH", "MODULE", "NETWORKING_STRING",
    "CONNECTIONS_STRING", "MEMORY_STRING", "CAMERA_STRING", "SOUNDCARD_STRING",
    "STORAGE_STRING", "SCREEN_RESOLUTION", "SCREEN_SIZE", "DISPLAY_STRING",
    "WEBSITE_PORTS_FRONT", "WEBSITE_PORTS_LEFT", "WEBSITE_PORTS_REAR",
    "WEBSITE_PORTS_RIGHT", "TYPE_C_PORTS_FRONT", "TYPE_C_PORTS_LEFT",
    "TYPE_C_PORTS_REAR", "TYPE_C_PORTS_RIGHT", "IDLE_C_COVER_1_1",
    "IDLE_C_COVER_1_2", "IDLE_C_COVER_1_3", "IDLE_C_COVER_2_1",
    "IDLE_C_COVER_2_2", "IDLE_C_COVER_2_3", "IDLE_C_COVER_3_1",
    "IDLE_C_COVER_3_2", "IDLE_C_COVER_3_3", "IDLE_D_COVER_1_1",
    "IDLE_D_COVER_1_2", "IDLE_D_COVER_1_3", "IDLE_D_COVER_2_1",
    "IDLE_D_COVER_2_2", "IDLE_D_COVER_2_3", "IDLE_D_COVER_3_1",
    "IDLE_D_COVER_3_2", "IDLE_D_COVER_3_3", "IDLE_POWER_SUPPLY_TEMPERATURE",
    "IDLE_ROOM_TEMPERATURE", "MAX_LOAD_C_COVER_1_1", "MAX_LOAD_C_COVER_1_2",
    "MAX_LOAD_C_COVER_1_3", "MAX_LOAD_C_COVER_2_1", "MAX_LOAD_C_COVER_2_2",
    "MAX_LOAD_C_COVER_2_3", "MAX_LOAD_C_COVER_3_1", "MAX_LOAD_C_COVER_3_2",
    "MAX_LOAD_C_COVER_3_3", "MAX_LOAD_D_COVER_1_1", "MAX_LOAD_D_COVER_1_2",
    "MAX_LOAD_D_COVER_1_3", "MAX_LOAD_D_COVER_2_1", "MAX_LOAD_D_COVER_2_2",
    "MAX_LOAD_D_COVER_2_3", "MAX_LOAD_D_COVER_3_1", "MAX_LOAD_D_COVER_3_2",
    "MAX_LOAD_D_COVER_3_3", "MAX_LOAD_POWER_SUPPLY_TEMPERATURE",
    "MAX_LOAD_ROOM_TEMPERATURE", "NOISE_IDLE_AVG", "NOISE_IDLE_MAX",
    "NOISE_IDLE_MIN", "NOISE_LOAD_AVG", "NOISE_LOAD_MAX", "NOISE_OFF",
    "PERFORMANCE_STRING", "PC_MARK_10", "CINEBENCH_MULTI_CORE",
    "CINEBENCH_SINGLE_CORE", "PRIME95_SCORE", "POWER_IDLE_AVG",
    "POWER_IDLE_MAX", "POWER_IDLE_MIN", "POWER_LOAD_AVG", "POWER_LOAD_MAX",
    "HEIGHT", "WIDTH", "DEPTH", "SIZE_STRING", "WEIGHT_KG", "WEIGHT_STRING",
    "LINKS_STRING", "ADDITIONAL_FEATURES_STRING", "VC", "BLADE_COUNT",
    "NUMBER_OF_FANS", "FAN_DIMENSION", "NUMBER_OF_HEATPIPES",
    "HEATPIPE_WIDTH", "LLM_PORTS_FRONT", "LLM_PORTS_LEFT", "LLM_PORTS_REAR",
    "LLM_PORTS_RIGHT", "SELECTED_THERMAL_IMAGE_FILE", "HASH_ID", "GET", "COSMOS_DB"
]

def fetch_page_data(page_num):
    url = f"https://dev1.notebook-check.com/index.php?id=98933&ns_ajax=1&language=2&ns_tt_content_uid=4503990&tagArray[]=16&typeArray[]=1&items_per_page=250&page={page_num}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return None
    return BeautifulSoup(response.content, 'html.parser')

def extract_laptop_data(laptop):
    if not laptop.find("span", class_="introa_review_specs_med"):
        return None

    laptop_url = laptop.get('href')
    laptop_title_tag = laptop.find('h2', class_='introa_title')
    if not laptop_title_tag:
        return None

    rating_span = laptop_title_tag.find('span', class_='rating')
    if not rating_span:
        return None

    laptop_title = ' '.join([item.strip() for item in laptop_title_tag.find_all(string=True) if item.parent.name != 'span'])
    laptop_comments_tag = laptop.find('div', class_='introa_rm_abstract')
    laptop_comments = ' '.join([item.string.strip() for item in laptop_comments_tag.find_all(recursive=False, string=True, class_=lambda x: x != 'itemauthordate')])

    laptop_published_date_int = int(laptop.find('span', class_='itemdate')['data-crdate'])
    laptop_published_date = datetime.datetime.fromtimestamp(laptop_published_date_int)
    formatted_date = laptop_published_date.strftime('%Y-%m-%dT%H:%M:%S.%f')
    laptop_published_date_string = laptop_published_date.strftime('%Y-%m-%d %H:%M')

    hash_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3] + str(uuid.uuid4().hex)[:15]

    return {
        "HASH_ID": hash_id,
        "URL": laptop_url,
        "GET": "N",
        "TITLE": html_text.extract_text(laptop_title).encode('ascii', 'ignore').decode(),
        "COMMENTS": html_text.extract_text(laptop_comments).encode('ascii', 'ignore').decode(),
        "PUBLISHED_DATE_STRING": laptop_published_date_string,
        "PUBLISHED_DATE": formatted_date,
        "COSMOS_DB": "N"
    }

def get_data(page_num, existing_urls):
    soup = fetch_page_data(page_num)
    if not soup:
        return None

    laptops = soup.find_all('a', class_='introa_large introa_review')
    if not laptops:
        return None

    extracted_data = []
    for laptop in laptops:
        data = extract_laptop_data(laptop)
        if data:
            laptop_url = data["URL"]
            if laptop_url in existing_urls:
                continue
            laptop_published_date = data["PUBLISHED_DATE"]
            if laptop_published_date < datetime.datetime(2023, 5, 27):
                return False, extracted_data
            extracted_data.append(data)

    return True, extracted_data

def load_existing_urls(file_path):
    if not os.path.exists(file_path):
        return set()

    df = pd.read_csv(file_path, encoding="utf-8-sig")
    urls = set(df["URL"].tolist())

    # Apply the check for "/https" in the URL and adjust if necessary (to check for web archive url)
    updated_urls = set()
    for url in urls:
        if "/https" in url:
            url = "https" + url.split("/https")[1]
        updated_urls.add(url)

    return updated_urls

def write_to_csv(data, file_path, headers):
    df = pd.DataFrame(data)
    file_exists = os.path.exists(file_path)
    
    if file_exists:
        existing_df = pd.read_csv(file_path, encoding="utf-8-sig")
        df = pd.concat([existing_df, df], ignore_index=True)
    else:
        # Ensure all headers are written even if no data rows are available
        empty_df = pd.DataFrame(columns=headers)
        df = pd.concat([empty_df, df], ignore_index=True)

    df.sort_values(by='PUBLISHED_DATE', ascending=False).to_csv(file_path, index=False, encoding="utf-8-sig")


def main():
    start_time = time.time()
    page_num = 0
    all_extracted_data = []
    existing_urls = load_existing_urls(CSV_FILE_PATH)

    while True:
        result, extracted_data = get_data(page_num, existing_urls)
        if result is False:
            break
        all_extracted_data.extend(extracted_data)
        page_num += 1

    if all_extracted_data:
        if not os.path.exists(OUTPUT_CSV_FOLDER):
            os.mkdir(OUTPUT_CSV_FOLDER)
        write_to_csv(all_extracted_data, CSV_FILE_PATH, CSV_HEADERS)
        print(f"Extracted rows: {len(all_extracted_data)}")

    end_time = time.time()
    print(f"Total time taken: {round(end_time - start_time, 2)} seconds")

if __name__ == "__main__":
    # Get the current working directory
    current_dir = os.getcwd()

    # Extract the actual directory name from the current path
    current_dir_name = os.path.basename(current_dir)

    # Check if the current directory name matches the expected name
    if current_dir_name != CWD:
        print(f"Incorrect working directory. Please cd into {CWD}")
    else:
        main()
