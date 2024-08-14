import json
import os
import re
import shutil
import uuid
import requests
import csv
import pandas as pd
import datetime
import time
from lxml import html
from lxml import etree
import html_text
import database_api
from image_downloader import download_and_process_images
from ultrabook_utils import get_hash_id, get_dimensions, get_depth, get_table_data, get_ul_data, get_section_key, get_cinebench, capacity_mah, capacity_wh, battery
from fake_useragent import UserAgent
ua = UserAgent()

def get_data(page_num):
    headers = {'User-Agent': ua.random}
    url = f"https://www.ultrabookreview.com/wp-json/wp/v2/posts?categories=22&per_page=100&page={page_num}&orderby=date"

    cnxn, cursor = database_api.create_connection()
    cnxn.autocommit = True
    # Send a GET request to the URL
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Parse the HTML content with BeautifulSoup
        products = response.json()
        # Loop through each laptop and extract information
        if products:
            
            for num, product in enumerate(products):
                    parent_hash_id = get_hash_id()
                    brand_name = None
                    model_name = None
                    comments = None
                    pros = None
                    cons = None
                    score = None
                    product_header = None
                    processor = None
                    processor_string = None
                    graphics_adapter = None
                    graphics_adapter_string = None
                    memory = None
                    display = None
                    mainboard = None
                    storage = None
                    soundcard = None
                    connections = None
                    networking = None
                    ports = None
                    size = None
                    height = None 
                    width = None 
                    depth = None
                    battery_string = None
                    battery_type = None
                    battery_mah = None
                    battery_wh = None
                    battery_series = None
                    battery_parallel = None
                    operating_system = None
                    camera = None
                    additional_features = None
                    weight = None
                    price = None
                    released = None
                    links = None
                    noise_level_idle = None
                    noise_level_load = None
                    temp_top_1_2 = None
                    temp_top_2_2 = None
                    temp_top_max = None
                    temp_top_avg = None
                    temp_bottom_1_2 = None
                    temp_bottom_2_2 = None
                    temp_bottom_max = None
                    temp_bottom_avg = None
                    performance = None
                    pc_mark10 = None
                    cover_photo_url = None
                    cinebench_single = None
                    cinebench_multi = None
                    published_date = None
                    
                    model_name = ' '.join(str(product['slug']).split("-review")[0].split("-"))
                    product_url = product['link']
                    product_title = product['title']['rendered']
                    product_content = product['content']['rendered']

                    query_url = f"SELECT URL FROM ULTRA_BOOK_REVIEW WHERE URL = '{product_url}'"
                    cursor.execute(query_url)
                    url_exists = cursor.fetchall()
                    if len(url_exists)>0:
                        print(f"Exists already: {product_url}")
                        print("="*40)
                        continue
                    r = requests.get(product_url)
                    print(f"{product_url}, row_num: {num+1}/{len(products)}")
                    if r.status_code == 200:
                        doc_url = etree.HTML(r.content)
                        script_tag = doc_url.xpath('//*[@id="main"]/script[@type="application/ld+json"]')
                        if len(script_tag)!=0:
                            json_data = json.loads(script_tag[0].text)
                            brand_name = json_data['brand']['name']
                            comments = html_text.extract_text(json_data['description']).encode('ascii', 'ignore').decode()
                            score = json_data['review']['reviewRating']['ratingValue']+" / "+json_data['review']['reviewRating']['bestRating']
                        else:
                            brand_name = product_title.split()[0]

                        product_header = html_text.extract_text(''.join(doc_url.xpath('//*[@id="title-main-review"]//text()'))).encode('ascii', 'ignore').decode()

                        pros = doc_url.xpath('//*[@class="revgood"]/ul//text()')
                        pros[0] = pros[0].strip('\r\n')
                        pros[-1] = pros[-1].rstrip('\r\n')
                        pros = ' '.join(pros)
                        cons = doc_url.xpath('//*[@class="revbad"]/ul//text()')
                        cons[0] = cons[0].strip('\r\n')
                        cons[-1] = cons[-1].rstrip('\r\n')
                        cons = ' '.join(cons)

                        price = html_text.extract_text(''.join(doc_url.xpath('//*[@class="pricerange"]//text()')).replace("from", "")).encode('ascii', 'ignore').decode()
                        price_check = price.split()
                        if len(price_check)>1 and price_check[1].lower() in ["euro", "eur"]:
                            price_converted = float(price_check[0].replace('.', '').replace(',', '.')) * 1.09
                            price = "$" + str(round(price_converted))
                        cover_photo_url = ''.join(doc_url.xpath('//*[@id="reviewthumb"]/img/@data-lazy-src')) or ''.join(doc_url.xpath('//*[@id="reviewthumb"]/img/@src'))
                        published_date = html_text.extract_text(''.join(doc_url.xpath('//*[@class="updated"]//text()'))).encode('ascii', 'ignore').decode()


                    if product_content:
                        doc = html.document_fromstring(product_content)

                        # get specs
                        main_spec_div = doc.xpath('//table/tbody')
                        all_specs_data = []
                        if main_spec_div:
                            for spec in main_spec_div[0]:
                                spec_title = spec.xpath("./td[1]//text()")
                                spec_value = spec.xpath("./td[2]//text()")

                                if spec_title:
                                    spec_title = spec_title[0].lower()
                                    if spec_value:
                                        spec_value = html_text.extract_text(''.join(spec_value)).encode('ascii', 'ignore').decode()

                                    if "processor" in spec_title:
                                        processor = spec_value.split(',')[0]
                                        processor_string = spec_value
                                        if processor_string:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Processor', "VALUE": processor_string, "PARENT_HASH_ID": parent_hash_id})
                                    elif "video" in spec_title:
                                        graphics_adapter = spec_value
                                        graphics_adapter_string = spec_value
                                        if graphics_adapter_string:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Video', "VALUE": graphics_adapter_string, "PARENT_HASH_ID": parent_hash_id})
                                    elif "memory" in spec_title:
                                        memory = spec_value
                                        if memory:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Memory', "VALUE": memory, "PARENT_HASH_ID": parent_hash_id})
                                    elif "screen" in spec_title or "display" in spec_title:
                                        display = spec_value
                                        if display:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Screen', "VALUE": display, "PARENT_HASH_ID": parent_hash_id})
                                    elif "mainboard" in spec_title:
                                        mainboard = spec_value
                                        if mainboard:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Mainboard', "VALUE": mainboard, "PARENT_HASH_ID": parent_hash_id})
                                    elif "storage" in spec_title:
                                        storage = spec_value
                                        if storage:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Storage', "VALUE": storage, "PARENT_HASH_ID": parent_hash_id})
                                    elif "soundcard" in spec_title:
                                        soundcard = spec_value
                                        if soundcard:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Soundcard', "VALUE": soundcard, "PARENT_HASH_ID": parent_hash_id})
                                    elif "connectivity" in spec_title:
                                        connections = spec_value
                                        if connections:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Connectivity', "VALUE": connections, "PARENT_HASH_ID": parent_hash_id})
                                    elif "ports" in spec_title:
                                        ports = spec_value
                                        if ports:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Ports', "VALUE": ports, "PARENT_HASH_ID": parent_hash_id})
                                    elif "networking" in spec_title:
                                        networking = spec_value
                                        if networking:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Networking', "VALUE": networking, "PARENT_HASH_ID": parent_hash_id})
                                    elif "size" in spec_title:
                                        size = spec_value
                                        if size:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Size', "VALUE": size, "PARENT_HASH_ID": parent_hash_id})
                                        height = get_dimensions(size, "h")
                                        width = get_dimensions(size, "w")
                                        depth = get_depth(size, ['d', 'l'])
                                    elif "battery" in spec_title:
                                        battery_string = spec_value
                                        if battery_string:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Battery', "VALUE": battery_string, "PARENT_HASH_ID": parent_hash_id})
                                        battery_type = battery(battery_string, format=True)
                                        battery_mah = capacity_mah(battery_string)
                                        battery_wh = capacity_wh(battery_string)
                                        battery_series = battery(battery_string, battery_series=True)
                                        battery_parallel = battery(battery_string, battery_series=False)
                                    elif "operating system" in spec_title:
                                        operating_system = spec_value
                                        if operating_system:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Operating system', "VALUE": operating_system, "PARENT_HASH_ID": parent_hash_id})
                                    elif "camera" in spec_title:
                                        camera = spec_value
                                        if camera:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Camera', "VALUE": camera, "PARENT_HASH_ID": parent_hash_id})
                                    elif "extras" in spec_title:
                                        additional_features = spec_value
                                        if additional_features:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Extras', "VALUE": additional_features, "PARENT_HASH_ID": parent_hash_id})
                                    elif "weight" in spec_title:
                                        weight = spec_value
                                        if weight:
                                            all_specs_data.append({"HASH_ID": get_hash_id(), "KEY": 'Weight', "VALUE": weight, "PARENT_HASH_ID": parent_hash_id})
                            
                        else:
                            continue
                        
                        # get sections
                        all_h_tags = doc_url.xpath('//*[@id="content-area"]//*[starts-with(local-name(), "h")]')
                        all_h_tags = all_h_tags[1:-1]
                        all_sections_data = []
                        for h_num, cur_h in enumerate(all_h_tags):
                            section_string = cur_h.xpath(".//text()")
                            if len(section_string)==0:
                                continue
                            section_string = section_string[0]
                            key = get_section_key(section_string)
                            next_h = None
                            if h_num+1< len(all_h_tags):
                                next_h = all_h_tags[h_num+1]

                            cur_id = cur_h.xpath("self::h2/@id | self::h2/span/@id | self::h3/span/@id | self::h4/span/@id")[0]
                            if next_h is not None:
                                next_id = next_h.xpath("self::h2/@id | self::h2/span/@id | self::h3/span/@id | self::h4/span/@id")[0]

                            elements_between = cur_h.xpath(
                            f'//*[self::h2 or self::h3 or self::h4][@id="{cur_id}" or span/@id="{cur_id}"]/following-sibling::*'
                            f'[following-sibling::*[self::h2 or self::h3 or self::h4][@id="{next_id}" or span/@id="{next_id}"]]'
                            )
                            this_section_data = {"images": [], "data": [], "key_points": []}

                            for element in elements_between:                         
                                if 'hardware' in section_string.lower() or 'noise' in section_string.lower() :
                                    get_section_images = element.xpath(".//a/@href")
                                    get_section_images_two = None
                                    if element.tag == 'div':
                                        get_section_images_two = element.xpath("img")
                                    for image_url in get_section_images:
                                        image_name = image_url.split("/")[-1]
                                        if "internal" in image_name or 'cooling' in image_name:
                                            # print(f"{image_url}")
                                            this_section_data['images'].append(image_url)
                                    if get_section_images_two:
                                        for image in get_section_images_two:
                                            image_url = image.get("src")
                                            image_name = image_url.split("/")[-1]
                                            if not "." in image_name:
                                                image_url = image.get("data-lazy-src")
                                            # print(f"{image_url}")
                                            this_section_data['images'].append(image_url)
                                if element.tag == "ul":
                                    if element.tag == "ul":
                                        keypoints = get_ul_data(element)
                                        this_section_data['key_points'] = this_section_data['key_points'] + keypoints
                                        for keypoint in keypoints:
                                            if "R23" in keypoint and (cinebench_single is None or cinebench_multi is None):
                                                cinebench_single = get_cinebench(keypoint, 'single')
                                                cinebench_multi = get_cinebench(keypoint, 'multi')
                                            # this_section_data['key_points'].append(keypoint)
                                            # if 'hardware' in section_string.lower() or 'performance' in section_string.lower():
                                                
                                    elif element.tag == "table":
                                        table = get_table_data(element)
                                        this_section_data['data'].append(table)
                                        # for t in table:
                                        #     this_section_data['data'].append(t)
                            scraped_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            all_sections_data.append({"HASH_ID":get_hash_id(), "SECTION_KEY": key, "SECTION_TITLE": section_string, 
                                                        "SECTION_DATA": this_section_data, "CREATED_AT": scraped_time,
                                                        "MODIFIED_AT": scraped_time, "PARENT_HASH_ID": parent_hash_id})

                        fieldnames_five = ['HASH_ID', 'URL', 'TITLE', 'BRAND', 'MODEL', 'COMMENTS', 'SCORE', 'PROS', 'CONS', 'PRODUCT', 'PROCESSOR', 'PROCESSOR_STRING', 'GRAPHICS_ADAPTER', 'GRAPHICS_ADAPTER_STRING', 'MEMORY_STRING', 'DISPLAY_STRING', 'MAINBOARD_STRING', 'STORAGE_STRING', 'SOUNDCARD_STRING', 'CONNECTIONS_STRING', 'NETWORKING_STRING', 'SIZE_STRING', 'HEIGHT', 'WIDTH', 'DEPTH', 'BATTERY_STRING', "BATTERY", "BATTERY_PARALLEL", "BATTERY_SERIES", "CAPACITY_MAH", "CAPACITY_WH", 'OPERATING_SYSTEM_STRING', 'CAMERA_STRING', 'ADDITIONAL_FEATURES_STRING', 'RELEASED_STRING', 'WEIGHT_STRING', 'PRICE_STRING', 'LINKS_STRING', 'PORTS', 'NOISE_LEVEL_IDLE_STRING', 'NOISE_LEVEL_LOAD_STRING', 'TEMP_TOP_1_2', 'TEMP_TOP_2_2', 'TEMP_TOP_MAX', 'TEMP_TOP_AVG', 'TEMP_BOTTOM_1_2', 'TEMP_BOTTOM_2_2', 'TEMP_BOTTOM_MAX', 'TEMP_BOTTOM_AVG', 'PERFORMANCE', 'PC_MARK_10', "CINEBENCH_MULTICORE", "CINEBENCH_SINGLECORE", 'COVER_IMAGE', 'PUBLISHED_DATE', 'CREATED_AT', 'MODIFIED_AT', 'CUST_NUMBER_OF_BLADE_COUNT',
                        'CUST_NUMBER_OF_FANS', 'CUST_NUMBER_OF_HEATPIPES']	

                        placeholders_five = ', '.join(['?'] * len(fieldnames_five))						  
                        table_name_five = 'ULTRA_BOOK_REVIEW' 
                        query_five = f"INSERT INTO {table_name_five} ({', '.join(fieldnames_five)}) VALUES ({placeholders_five})"
                        scraped_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        main_dict = {
                            'HASH_ID': parent_hash_id,
                            'URL': product_url,
                            'TITLE': product_title,
                            'BRAND': brand_name,
                            'MODEL': model_name,
                            'COMMENTS':comments,
                            'SCORE':score,
                            'PROS':pros,
                            'CONS':cons,
                            'PRODUCT': product_header,
                            'PROCESSOR': processor,
                            'PROCESSOR_STRING': processor_string,
                            'GRAPHICS_ADAPTER': graphics_adapter,
                            'GRAPHICS_ADAPTER_STRING': graphics_adapter_string,
                            'MEMORY_STRING': memory,
                            'DISPLAY_STRING': display,
                            'MAINBOARD_STRING': mainboard,
                            'STORAGE_STRING': storage,
                            'SOUNDCARD_STRING': soundcard,
                            'CONNECTIONS_STRING': connections,
                            'NETWORKING_STRING': networking,
                            'SIZE_STRING': size,
                            'HEIGHT': height,
                            'WIDTH': width,
                            'DEPTH': depth,
                            'BATTERY_STRING': battery_string,
                            "BATTERY": battery_type,
                            "BATTERY_PARALLEL": battery_parallel,
                            "BATTERY_SERIES": battery_series,
                            "CAPACITY_MAH": battery_mah,
                            "CAPACITY_WH": battery_wh,
                            'OPERATING_SYSTEM_STRING': operating_system,
                            'CAMERA_STRING': camera,
                            'ADDITIONAL_FEATURES_STRING': additional_features,
                            'RELEASED_STRING': released,
                            'WEIGHT_STRING': weight,
                            'PRICE_STRING': price,
                            'LINKS_STRING': links,
                            'PORTS': ports,
                            'NOISE_LEVEL_IDLE_STRING': noise_level_idle,
                            'NOISE_LEVEL_LOAD_STRING': noise_level_load,
                            'TEMP_TOP_1_2': temp_top_1_2,
                            'TEMP_TOP_2_2': temp_top_2_2,
                            'TEMP_TOP_MAX': temp_top_max,
                            'TEMP_TOP_AVG': temp_top_avg,
                            'TEMP_BOTTOM_1_2': temp_bottom_1_2,
                            'TEMP_BOTTOM_2_2': temp_bottom_2_2,
                            'TEMP_BOTTOM_MAX': temp_bottom_max,
                            'TEMP_BOTTOM_AVG': temp_bottom_avg,
                            'PERFORMANCE': performance,
                            'PC_MARK_10': pc_mark10,
                            "CINEBENCH_MULTICORE": cinebench_multi,
                            "CINEBENCH_SINGLECORE": cinebench_single,
                            'COVER_IMAGE': cover_photo_url,
                            'PUBLISHED_DATE': published_date,
                            'CREATED_AT': scraped_time, 
                            'MODIFIED_AT': scraped_time,
                            'CUST_NUMBER_OF_BLADE_COUNT': 0,
                            'CUST_NUMBER_OF_FANS': 0, 
                            'CUST_NUMBER_OF_HEATPIPES': 0
                            }
                        row_values_five = tuple(main_dict.values())
                        cursor.execute(query_five, row_values_five)
                        cnxn.commit()


                        fieldnames_one = ['HASH_ID', '[KEY]', 'VALUE', 'PARENT_HASH_ID']
                        # fieldnames_one = [f"[{name}]" if name in ['KEY'] else name for name in fieldnames_four]
                        table_name_one = 'ULTRA_BOOK_REVIEW_SPECS'
                        placeholders_one = ', '.join(['?'] * len(fieldnames_one))
                        query_one = f"INSERT INTO {table_name_one} ({', '.join(fieldnames_one)}) VALUES ({placeholders_one})"
                        for row_data in all_specs_data:
                            row_values_one = tuple(row_data.values())
                            cursor.execute(query_one, row_values_one)
                            cnxn.commit()

                        fieldnames_two = ['HASH_ID', 'SECTION_KEY', 'SECTION_TITLE', 'CREATED_AT', 'MODIFIED_AT','PARENT_HASH_ID']
                        table_name_two = 'ULTRA_BOOK_REVIEW_SECTION'
                        placeholders_two = ', '.join(['?'] * len(fieldnames_two))
                        query_two = f"INSERT INTO {table_name_two} ({', '.join(fieldnames_two)}) VALUES ({placeholders_two})"
                        for row_data in all_sections_data:
                            # print(f"row_data: {row_data}")
                            filtered_dict = {key: value for key, value in row_data.items() if key != 'SECTION_DATA'}
                            row_values_two = tuple(filtered_dict.values())
                            cursor.execute(query_two, row_values_two)
                            cnxn.commit()
                            if len(row_data['SECTION_DATA']['data'])!=0 or len(row_data['SECTION_DATA']['key_points'])!=0:

                                items = [{"data_type": "TABLE", "data": row_data['SECTION_DATA']['data']}, 
                                        {"data_type": "KEYPOINT", "data": row_data['SECTION_DATA']['key_points']}]
                                
                                fieldnames_three = ['HASH_ID', 'DATA_TYPE', 'DATA', 'CREATED_AT', 'MODIFIED_AT','PARENT_HASH_ID']
                                table_name_three = 'ULTRA_BOOK_REVIEW_SECTION_DATA'
                                placeholders_three = ', '.join(['?'] * len(fieldnames_three))
                                query_three = f"INSERT INTO {table_name_three} ({', '.join(fieldnames_three)}) VALUES ({placeholders_three})"
                                for item in items:
                                    if len(item['data'])!=0:
                                        scraped_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                        item_dict = {'HASH_ID': get_hash_id(), 
                                                    'DATA_TYPE': item['data_type'],
                                                    'DATA': json.dumps(item['data']),
                                                    'CREATED_AT': scraped_time, 
                                                    'MODIFIED_AT': scraped_time, 
                                                    'PARENT_HASH_ID': row_data['HASH_ID']
                                                    }
             
                                        row_values_three = tuple(item_dict.values())
                                        cursor.execute(query_three, row_values_three)
                                        cnxn.commit()

                            if len(row_data['SECTION_DATA']['images'])!=0:
        
                                processed_images = download_and_process_images(row_data['SECTION_DATA']['images'], row_data['HASH_ID'])
                                fieldnames_four = ['HASH_ID', 'IMAGE_URL', 'FILE_DATA', 'FILE_NAME', 'FILE_SIZE', 'UPLOAD_TIME', 'PARENT_HASH_ID']
                                table_name_four = 'ULTRA_BOOK_REVIEW_IMAGES'
                                placeholders_four = ', '.join(['?'] * len(fieldnames_four))
                                query_four = f"INSERT INTO {table_name_four} ({', '.join(fieldnames_four)}) VALUES ({placeholders_four})"
                                # print(processed_images)
                                for image in processed_images:
                                    image['FILE_DATA'] = bytes.fromhex(image['FILE_DATA'])
                                    row_values_four = tuple(image.values())
                                    cursor.execute(query_four, row_values_four)
                                    cnxn.commit()
                        
                        print("="*40)
                        
                    else:
                        continue
            cursor.close()
            cnxn.close()
            print(f"done with page:{page_num}")
            return True
        else:
            return False
    else:
        print("Failed to retrieve the webpage. Status code:", response.status_code)
        return False

result = None
page_num = 1
start_time = time.time()

# result=get_data(page_num)
while result!=False:
    result=get_data(page_num)
    page_num+=1

end_time = time.time()
print(end_time-start_time)