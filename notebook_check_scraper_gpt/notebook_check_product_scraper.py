import json
import os
import re
import time
import warnings
import pandas as pd
import requests
from lxml import etree
import html_text
from image_downloader import download_and_process_images
from notebook_check_utils import get_prime95_score, get_cinebench, get_battery_type, get_battery_tech, bluetooth, module, get_pl1, get_pl2, get_tdp, wifi, ports_info, capacity_mah, capacity_wh, get_additional_data, get_temp_limits
from archive_url_scraper import get_archive_urls
from gpt_string_splitter import gpt_html_extract
from decouple import config

warnings.simplefilter(action='ignore', category=FutureWarning)
# URL of the website

CWD = config("CWD")
OUTPUT_CSV_FOLDER = config("OUTPUT_CSV_FOLDER")
OUTPUT_CSV_NAME = config("OUTPUT_CSV_NAME")
CSV_FILE_PATH = f"{OUTPUT_CSV_FOLDER}/{OUTPUT_CSV_NAME}"

def check_xpath(doc, xpath, index):
    try:
        value = doc.xpath(xpath)[index]
        return value
    except Exception as e:
        return None
    
def get_data(row_data, archive_url, row_num, nb_check_url):
    try:
        if archive_url:
            time.sleep(3)
            request_headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'cookie': 'nbc_continent=AS; nbc_beu=false; nbc_countryid=37; nbc_countryshortcode=in; nbc_nbcompare=; nbc_call=3',
                'if-modified-since': 'Wed, 12 Jun 2024 14:41:21 GMT',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            }

            # Send a GET request to the URL
            response = requests.get(archive_url, headers=request_headers)
            
            if response.status_code == 200:
                doc = etree.HTML(response.content)
                images = []
                images_added_to_db = False

                product_data = {}
                hash_id = row_data["HASH_ID"]
                product_data["URL"] = archive_url
                product_data["GET"] = "Y"

                ### brand_name
                script_tag = doc.xpath('//*[@class="tx-nbc2fe-pi1"]/script[@type="application/ld+json"]')
                if script_tag:
                        json_data = json.loads(script_tag[0].text)
                        product_data["BRAND"] = json_data['brand']['name']
                else:
                    return None
                
                ### review_text
                review_elements = doc.xpath('//*[@id="content"]/div[2]/div[2]/div[2]/p//text()')
                # review_text_list = []
                # for el in review_elements:
                #     review_text_list.append(el.text)
                review_text = ''.join(review_elements)
                product_data["REVIEW"] = html_text.extract_text(review_text).encode('ascii', 'ignore').decode()

                ### product header
                product_header = doc.xpath('//*[@class="specs_header"]//text()')
                product_header = ''.join(product_header)
                product_data["PRODUCT"] = html_text.extract_text(product_header).encode('ascii', 'ignore').decode()

                ### all specs
                all_specs = doc.xpath('//*[@class="specs_element"]')

                for spec in all_specs:
                    spec_title = spec.xpath("./div[1]/text()")
                    spec_value = spec.xpath("./div[2]/text()")
                
                    if spec_title:
                        spec_title = spec_title[0].lower()
                        if spec_value:
                            spec_value = html_text.extract_text(spec_value[0]).encode('ascii', 'ignore').decode()

                        if spec_title=="processor":
                            product_data["PROCESSOR"] = html_text.extract_text(check_xpath(spec, "./div[2]/a/text()", 0)).encode('ascii', 'ignore').decode()
                            if(spec_value):
                                product_data["PROCESSOR_STRING"] = spec_value
                                product_data["PROCESSOR_PL1"] = get_pl1(spec_value)
                                product_data["PROCESSOR_PL2"] = get_pl2(spec_value)
                            
                        elif spec_title=="graphics adapter":
                            product_data["GRAPHICS_ADAPTER"] = html_text.extract_text(check_xpath(spec, "./div[2]/a/text()", 0)).encode('ascii', 'ignore').decode()
                            if(spec_value):
                                product_data["GRAPHICS_ADAPTER_STRING"] = product_data["GRAPHICS_ADAPTER"] + spec_value
                                product_data["GRAPHICS_ADAPTER_TDP"] = get_tdp(product_data["GRAPHICS_ADAPTER_STRING"])
                        elif spec_title=="memory":
                            spec_value = spec.xpath("./div[2]//text()")
                            product_data["MEMORY_STRING"] = html_text.extract_text(''.join(spec_value)).encode('ascii', 'ignore').decode()
                        elif spec_title=="display":
                            product_data["DISPLAY_STRING"] = spec_value
                        elif spec_title=="mainboard":
                            product_data["MAINBOARD_STRING"] = spec_value
                        elif spec_title=="storage":
                            spec_value = spec.xpath("./div[2]//text()")
                            product_data["STORAGE_STRING"] = html_text.extract_text(''.join(spec_value)).encode('ascii', 'ignore').decode()
                        elif spec_title=="soundcard":
                            product_data["SOUNDCARD_STRING"] = spec_value
                        elif spec_title=="connections":
                            product_data["CONNECTIONS_STRING"] = spec_value
                        elif spec_title=="networking":
                            product_data["NETWORKING_STRING"] = spec_value
                            # wan_string = wan(networking)
                            product_data["WIFI"] = html_text.extract_text(wifi(spec_value)).encode('ascii', 'ignore').decode()
                            product_data["MODULE"] = html_text.extract_text(module(spec_value)).encode('ascii', 'ignore').decode()
                            product_data["BLUETOOTH"] = html_text.extract_text(bluetooth(spec_value)).encode('ascii', 'ignore').decode()
                            
                        elif spec_title=="size":
                            product_data["SIZE_STRING"] = spec_value
                            size_values = spec_value.split(":")[1].strip().split("x")
                            product_data["HEIGHT"] = float(size_values[0].strip())
                            product_data["WIDTH"] = float(size_values[1].strip())
                            product_data["DEPTH"] = float(size_values[2].split("(")[0].strip())
                        elif spec_title=="battery":
                            product_data["BATTERY_STRING"] = spec_value
                            product_data["BATTERY_TECHNOLOGY"] = get_battery_tech(spec_value)
                            product_data["BATTERY_TYPE"] = get_battery_type(spec_value, format=True)
                            product_data["BATTERY_MAH"] = capacity_mah(spec_value)
                            product_data["BATTERY_WH"] = capacity_wh(spec_value)
                            product_data["BATTERY_SERIES"] = get_battery_type(spec_value, battery_series=True)
                            product_data["BATTERY_PARALLEL"] = get_battery_type(spec_value, battery_series=False)
                        elif spec_title=="operating system":
                            product_data["OPERATING_SYSTEM_STRING"] = spec_value
                        elif spec_title=="camera":
                            product_data["CAMERA_STRING"] = spec_value
                        elif spec_title=="additional features":
                            product_data["ADDITIONAL_FEATURES_STRING"] = spec_value
                        elif spec_title=="weight":
                            # Change: weight regex
                            pattern = r'(\d+(\.\d+)?)\s*kg|(\d+(\.\d+)?)\s*g'
                            match = re.search(pattern, spec_value)
                            if match:
                                if match.group(1):  # This means the weight is in kilograms
                                    weight_kg = float(match.group(1))
                                elif match.group(3):  # This means the weight is in grams
                                    weight_kg = float(match.group(3)) / 1000
                                product_data["WEIGHT_KG"] = weight_kg
                            product_data["WEIGHT_STRING"] = spec_value
                        elif spec_title=="price":
                            product_data["PRICE_STRING"] = spec_value
                            price_check = spec_value.split()
                            if price_check[1].lower() in ["euro", "eur"]:
                                price_converted = float(price_check[0].replace('.', '').replace(',', '.')) * 1.09
                                product_data["PRICE_USD"] = round(price_converted)
                            else:
                                product_data["PRICE_USD"] = price_check[0]
                        elif spec_title=="links":
                            spec_value = spec.xpath("./div[2]/a/@href")
                            product_data["LINKS_STRING"] = ' | '.join(spec_value)
                
                ### battery
                battery_table = get_additional_data(doc, 'Battery')
                if battery_table is not None:
                    product_data["BATTERY_IDLE"] = battery_table.get('reader / idle', None)
                    product_data["BATTERY_LOAD"] = battery_table.get('load', None)
                    product_data["BATTERY_WIFI"] = battery_table.get('wifi v1.3', None)
                    product_data["BATTERY_H264"] = battery_table.get('h.264', None)

                ### noise level
                noise = get_additional_data(doc, 'Noise')
                if noise:
                    noise_off = noise.get('off / environment', None)
                    if not noise_off:
                        noise_off = noise.get('off/environment', None)

                    product_data["NOISE_OFF"] = noise_off
                    product_data["NOISE_IDLE_MAX"] = noise.get('idle maximum', None)
                    product_data["NOISE_IDLE_MIN"] = noise.get('idle minimum', None)
                    product_data["NOISE_IDLE_AVG"] = noise.get('idle average', None)
                    product_data["NOISE_LOAD_MAX"] = noise.get('load maximum', None)
                    product_data["NOISE_LOAD_AVG"] = noise.get('load average', None)

                if not product_data.get("MAINBOARD_STRING", None) \
                    and not product_data.get("SOUNDBOARD_STRING", None) \
                    and not product_data.get("NOISE_IDLE_AVG", None) \
                    and product_data.get("NOISE_LOAD_AVG", None):
                    # Product is not a laptop
                    return False
                
                # Change: power
                power = get_additional_data(doc, 'Power')
                if power:
                    product_data["POWER_IDLE_MAX"] = power.get('idle maximum', None)
                    product_data["POWER_IDLE_MIN"] = power.get('idle minimum', None)
                    product_data["POWER_IDLE_AVG"] = power.get('idle average', None)
                    product_data["POWER_LOAD_MAX"] = power.get('load maximum', None)
                    product_data["POWER_LOAD_AVG"] = power.get('load average', None)

                product_data["PRIME95_SCORE"] = get_prime95_score(doc, nb_check_url)

                # Change: added max load and temp  
                max_load, idle = get_temp_limits(doc)

                max_load_temp_caption = max_load['temp_caption']

                max_load_c_cover_dict = max_load['c_cover']
                product_data["MAX_LOAD_C_COVER_1_1"] = max_load_c_cover_dict["max_load_c_cover_1_1"] 
                product_data["MAX_LOAD_C_COVER_1_2"] = max_load_c_cover_dict["max_load_c_cover_1_2"] 
                product_data["MAX_LOAD_C_COVER_1_3"] = max_load_c_cover_dict["max_load_c_cover_1_3"] 
                product_data["MAX_LOAD_C_COVER_2_1"] = max_load_c_cover_dict["max_load_c_cover_2_1"] 
                product_data["MAX_LOAD_C_COVER_2_2"] = max_load_c_cover_dict["max_load_c_cover_2_2"] 
                product_data["MAX_LOAD_C_COVER_2_3"] = max_load_c_cover_dict["max_load_c_cover_2_3"] 
                product_data["MAX_LOAD_C_COVER_3_1"] = max_load_c_cover_dict["max_load_c_cover_3_1"] 
                product_data["MAX_LOAD_C_COVER_3_2"] = max_load_c_cover_dict["max_load_c_cover_3_2"] 
                product_data["MAX_LOAD_C_COVER_3_3"] = max_load_c_cover_dict["max_load_c_cover_3_3"] 
                
                max_load_d_cover_dict = max_load['d_cover']
                product_data["MAX_LOAD_D_COVER_1_1"] = max_load_d_cover_dict["max_load_d_cover_1_1"]
                product_data["MAX_LOAD_D_COVER_1_2"] = max_load_d_cover_dict["max_load_d_cover_1_2"]
                product_data["MAX_LOAD_D_COVER_1_3"] = max_load_d_cover_dict["max_load_d_cover_1_3"]
                product_data["MAX_LOAD_D_COVER_2_1"] = max_load_d_cover_dict["max_load_d_cover_2_1"]
                product_data["MAX_LOAD_D_COVER_2_2"] = max_load_d_cover_dict["max_load_d_cover_2_2"]
                product_data["MAX_LOAD_D_COVER_2_3"] = max_load_d_cover_dict["max_load_d_cover_2_3"]
                product_data["MAX_LOAD_D_COVER_3_1"] = max_load_d_cover_dict["max_load_d_cover_3_1"]
                product_data["MAX_LOAD_D_COVER_3_2"] = max_load_d_cover_dict["max_load_d_cover_3_2"]
                product_data["MAX_LOAD_D_COVER_3_3"] = max_load_d_cover_dict["max_load_d_cover_3_3"]

                idle_temp_caption = idle['temp_caption']

                idle_c_cover_dict = idle['c_cover']
                product_data["IDLE_C_COVER_1_1"] = idle_c_cover_dict["idle_c_cover_1_1"]
                product_data["IDLE_C_COVER_1_2"] = idle_c_cover_dict["idle_c_cover_1_2"]
                product_data["IDLE_C_COVER_1_3"] = idle_c_cover_dict["idle_c_cover_1_3"]
                product_data["IDLE_C_COVER_2_1"] = idle_c_cover_dict["idle_c_cover_2_1"]
                product_data["IDLE_C_COVER_2_2"] = idle_c_cover_dict["idle_c_cover_2_2"]
                product_data["IDLE_C_COVER_2_3"] = idle_c_cover_dict["idle_c_cover_2_3"]
                product_data["IDLE_C_COVER_3_1"] = idle_c_cover_dict["idle_c_cover_3_1"]
                product_data["IDLE_C_COVER_3_2"] = idle_c_cover_dict["idle_c_cover_3_2"]
                product_data["IDLE_C_COVER_3_3"] = idle_c_cover_dict["idle_c_cover_3_3"]

                idle_d_cover_dict = idle['d_cover']
                product_data["IDLE_D_COVER_1_1"] = idle_d_cover_dict["idle_d_cover_1_1"]
                product_data["IDLE_D_COVER_1_2"] = idle_d_cover_dict["idle_d_cover_1_2"]
                product_data["IDLE_D_COVER_1_3"] = idle_d_cover_dict["idle_d_cover_1_3"]
                product_data["IDLE_D_COVER_2_1"] = idle_d_cover_dict["idle_d_cover_2_1"]
                product_data["IDLE_D_COVER_2_2"] = idle_d_cover_dict["idle_d_cover_2_2"]
                product_data["IDLE_D_COVER_2_3"] = idle_d_cover_dict["idle_d_cover_2_3"]
                product_data["IDLE_D_COVER_3_1"] = idle_d_cover_dict["idle_d_cover_3_1"]
                product_data["IDLE_D_COVER_3_2"] = idle_d_cover_dict["idle_d_cover_3_2"]
                product_data["IDLE_D_COVER_3_3"] = idle_d_cover_dict["idle_d_cover_3_3"]

                ### performance
                performance_parent_div = doc.xpath("//div[contains(@class, 'csc-default')]//table[contains(@class, 'r_compare_bars') and contains(., 'CPU Performance Rating')]")
                if performance_parent_div:  
                    all_performance_tables = performance_parent_div[0].xpath("./following-sibling::table")
                    all_performance_tables.append(performance_parent_div[0])
                    performance_string_list = []
                    for table in all_performance_tables:
                        performance_title = check_xpath(table, ".//tr/td[contains(@class, 'prog_header')]/text()", 0)
                        multi_table_check = table.xpath(".//tr/td[contains(@class, 'settings_header')]")
                        multi_table_titles = []
                        if len(multi_table_check)>1:
                            for one_table in multi_table_check:
                                multi_table_titles.append(one_table.text)

                        performance_value = table.xpath(".//*[contains (@class,'referencespecs')]//span[contains(@class, 'r_compare_bars_value')]//*[not(self::span[contains(@class, 'r_compare_percent')])]//text()")
                        performance_value_unit = table.xpath(".//*[contains (@class,'referencespecs')]//span[contains(@class, 'r_compare_bars_value')]/text()")
                        if len(multi_table_titles)!=0:
                            combined_data = zip(multi_table_titles, performance_value, performance_value_unit)
                            performance_value = [f"{performance_title} / {title}: {value} {unit}" for title, value, unit in combined_data]
                            for item in performance_value:
                                performance_string_list.append(html_text.extract_text(''.join(item)).encode('ascii', 'ignore').decode())
                        else:                     
                            performance_string_list.append(performance_title+": "+html_text.extract_text(''.join(performance_value)).encode('ascii', 'ignore').decode()+" "+html_text.extract_text(''.join(performance_value_unit)).encode('ascii', 'ignore').decode())

                    product_data["CINEBENCH_SINGLE_CORE"] = get_cinebench(performance_string_list, 'single')
                    product_data["CINEBENCH_MULTI_CORE"] = get_cinebench(performance_string_list, 'multi')
                    product_data["PERFORMANCE_STRING"] = ' | '.join(performance_string_list)
                    

                ### pc mark10
                pc_mark_parent_div = doc.xpath("//div[contains(@class, 'csc-default')]//table[contains(@class, 'r_compare_bars') and contains(., 'PCMark 10')]")
                if pc_mark_parent_div:   
                    all_pc_mark_tables = pc_mark_parent_div[0].xpath("./following-sibling::table[contains(@class, 'r_compare_bars') and contains(., 'PCMark 10')]")
                    all_pc_mark_tables.append(pc_mark_parent_div[0])
                    pc_mark_string_list = []
                    for table in all_pc_mark_tables:
                        pc_mark_title = check_xpath(table, ".//tr[1]/td/text()", 0)
                        pc_mark_value = table.xpath(".//*[contains (@class,'referencespecs')]//span[contains(@class, 'r_compare_bars_value')]//*[not(self::span[contains(@class, 'r_compare_percent')])]//text()")
                        pc_mark_value_unit = table.xpath(".//*[contains (@class,'referencespecs')]//span[contains(@class, 'r_compare_bars_value')]/text()")
                        pc_mark_string_list.append(pc_mark_title.replace("PCMark 10 / ","")+": "+html_text.extract_text(''.join(pc_mark_value)).encode('ascii', 'ignore').decode()+" "+html_text.extract_text(''.join(pc_mark_value_unit)).encode('ascii', 'ignore').decode())
                    product_data["PC_MARK_10"] = ' | '.join(pc_mark_string_list)
                
                ### images
                def image_already_added(images, href):
                        # Check if the same href already exists in the list
                        for image in images:
                            if image['HREF'] == href:
                                print(f"Image with href '{href}' already exists in the list.")
                                return True
                            else:
                                return False
                            
                divElement = check_xpath(doc, "//div[@id='nbc_main']", 0)

                if divElement is not None and divElement!="":
                    imgsElement = divElement.xpath(".//img")
                    sn = 1
                    maintenance_text_div = doc.xpath("//div[contains(@class, 'csc-default')]//div[contains(@class, 'csc-header') and contains(., 'Maintenance')]")
                    if maintenance_text_div:
                        maintenance_images = maintenance_text_div[0].getnext().xpath(".//a")
                        if len(maintenance_images)==0:
                            maintenance_images = maintenance_text_div[0].getparent().getnext().xpath(".//a")
                        # print(len(maintenance_images))
                        for image in maintenance_images:
                            href = image.get("href")
                            if href.lower().endswith(("jpg", "png")) and not image_already_added(images, href):
                                img_title = image.get('title')
                                images.append({"SN": sn, "HREF": f"https://www.notebookcheck.net/{href}", "TITLE": img_title, "TYPE": "internal"})
                                sn += 1
                    
                    for imgElement in imgsElement:
                        src = imgElement.get('src')
                        parentElement = imgElement.getparent()
                        while parentElement is not None:
                            if parentElement.tag == "a":
                                href = parentElement.get("href")
                                if href.lower().endswith(("jpg", "png")) and not image_already_added(images, href):
                                    img_title = parentElement.get('title')
                                    images.append({"SN": sn, "HREF": f"https://www.notebookcheck.net/{href}", "TITLE": img_title, "TYPE": "general"})
                                    sn += 1
                                break
                            elif parentElement.tag == "source":
                                parentElement = parentElement.getparent().getparent()
                                if parentElement.tag == "a":
                                    href = parentElement.get("href")
                                    if href.lower().endswith(("jpg", "png")) and not image_already_added(images, href):
                                        img_title = parentElement.get('title')
                                        images.append({"SN": sn, "HREF": f"https://www.notebookcheck.net/{href}", "TITLE": img_title, "TYPE": "general"})
                                        sn += 1
                                    break
                            else:
                                break

                if len(images)!=0:
                    success = download_and_process_images(images, hash_id)
                    # if success:
                    #     images_added_to_db = True
                    connectivity_detected = False
                    try:
                        ports_previous_div = doc.xpath("//div[contains(@class, 'csc-default')]//div[contains(@class, 'csc-header') and contains(., 'Connectivity')]")
                        ports_image_text = ports_previous_div[0].getparent().xpath("following-sibling::div[contains(@class, 'csc-default')][1]//figure[@class='csc-textpic-image csc-textpic-last']/a/@title")
                        connectivity_detected = True
                        ports_data = ports_info(connectivity_detected, ports_image_text)
                    except IndexError:
                        all_image_text = []
                        for image in images:
                            all_image_text.append(image['TITLE'])
                        connectivity_detected = False
                        ports_data = ports_info(connectivity_detected, all_image_text)

                    product_data["WEBSITE_PORTS_LEFT"] = html_text.extract_text(ports_data['port_left']).encode('ascii', 'ignore').decode()
                    product_data["WEBSITE_PORTS_RIGHT"] = html_text.extract_text(ports_data['port_right']).encode('ascii', 'ignore').decode()
                    product_data["WEBSITE_PORTS_FRONT"] = html_text.extract_text(ports_data['port_front']).encode('ascii', 'ignore').decode()
                    product_data["WEBSITE_PORTS_REAR"] = html_text.extract_text(ports_data['port_rear']).encode('ascii', 'ignore').decode()

                def safe_concat(*args):
                    return ''.join([str(arg) if arg is not None else '' for arg in args])

                gpt_response = gpt_html_extract(
                        safe_concat("Display: ", product_data.get("DISPLAY_STRING", None), '\nMax Load: ', max_load_temp_caption, '\nIdle: ', idle_temp_caption, '\nLeft: ', product_data.get("WEBSITE_PORT_LEFT", None), '\nRight: ', product_data.get("WEBSITE_PORT_RIGHT", None), '\nRear: ', product_data.get("WEBSITE_PORT_REAR", None),'\nFront: ', product_data.get("WEBSITE_PORT_FRONT", None))
                    )
                if gpt_response:
                    product_data["SCREEN_SIZE"] = gpt_response.get("screen_size", "N/A")
                    product_data["SCREEN_RESOLUTION"] = gpt_response.get("screen_resolution", "N/A")
                    product_data["MAX_LOAD_POWER_SUPPLY_TEMPERATURE"] = gpt_response.get("max_load_power_supply_temperature", "N/A")
                    product_data["MAX_LOAD_ROOM_TEMPERATURE"] = gpt_response.get("max_load_room_temperature", "N/A")
                    product_data["IDLE_POWER_SUPPLY_TEMPERATURE"] = gpt_response.get("idle_power_supply_temperature", "N/A")
                    product_data["IDLE_ROOM_TEMPERATURE"] = gpt_response.get("idle_room_temperature", "N/A")
                    product_data["TYPE_C_PORTS_LEFT"] = gpt_response.get("type_c_ports_left", "N/A")
                    product_data["TYPE_C_PORTS_RIGHT"] = gpt_response.get("type_c_ports_right", "N/A")
                    product_data["TYPE_C_PORTS_REAR"] = gpt_response.get("type_c_ports_rear", "N/A")
                    product_data["TYPE_C_PORTS_FRONT"] = gpt_response.get("type_c_ports_front", "N/A")

                ### scraped time
                product_data["SCRAPED_TIME"] = (
                    hash_id[0:4] + "-" + hash_id[4:6] + "-" + hash_id[6:8] +
                    " " + hash_id[8:10] + ":" + hash_id[10:12] + ":" + hash_id[12:14] + ".000"
                )

                return product_data
            
            else:
                print(f"{row_num+1}. Failed to retrieve the webpage. Status code:", response.status_code)
                return None
        else:
            print(f"{row_num+1}. Failed to retrieve the webpage. Webpage not available on web archive.")
            return None
        
    except Exception as e:
        print(f"Error occured: {e}, URL: {nb_check_url}")
        return None

if __name__ == "__main__":
    # Get the current working directory
    current_dir = os.getcwd()

    # Extract the actual directory name from the current path
    current_dir_name = os.path.basename(current_dir)

    # Check if the current directory name matches the expected name
    if current_dir_name != CWD:
        print(f"Incorrect working directory. Please cd into {CWD}")
    else:
        start_time = time.time()
        
        # Load the DataFrame from the CSV file
        df = pd.read_csv(CSV_FILE_PATH, encoding="utf-8-sig")

        # Initialize a counter for batch processing
        batch_counter = 0

        # Process each row
        for row_num, row in df.iterrows():
            if row["GET"] == "N":
                nb_check_url = row['URL']
                first_ts_url, last_ts_url = get_archive_urls(nb_check_url)  # replace 'ColumnWithURL' with the actual column name containing the URL

                result = get_data(row, last_ts_url, row_num, nb_check_url)
                if result is None:
                    print(f"{row_num + 1}. Retrying..")
                    result = get_data(row, first_ts_url, row_num, nb_check_url)

                if result is None:
                    print(f'{row_num + 1}. Failed to fetch first and last URLs')
                    df.drop(row_num, inplace=True)  # Drop the row if data couldn't be fetched
                elif result == False:
                    print(f'{row_num + 1}. Product is not a laptop')
                    df.drop(row_num, inplace=True)  # Drop the row if the product is not a laptop
                else:
                    print(f"{row_num + 1}. Success: {nb_check_url}")
                    for key, value in result.items():
                        df.at[row_num, key] = value  # Update the row with the retrieved data

                # Increment the batch counter
                batch_counter += 1

                # Check if the batch size has been reached
                if batch_counter == 5:
                    # Sort and save the batch to the CSV file
                    df.sort_values(by='PUBLISHED_DATE', ascending=False).to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
                    print(f"Batch of 5 rows saved to {CSV_FILE_PATH}.")
                    # Reset the batch counter
                    batch_counter = 0

                # Wait after each product
                time.sleep(5)

        # Save any remaining rows that were not saved in the last batch
        if batch_counter > 0:
            df.sort_values(by='PUBLISHED_DATE', ascending=False).to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
            print(f"Final batch of {batch_counter} rows saved to {CSV_FILE_PATH}.")

        end_time = time.time()
        print(f"Total time taken {round(end_time-start_time, 2)} seconds")