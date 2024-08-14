import re
from math import ceil as round_up

R23_REGX_SINGLE = R23_REGX_SINGLE = re.compile(
    r"\d+|(Cinebench R23\ /\ Single\ Core:\d+)|Cinebench R23-Single\ Core:\d+|(Cinebench R23-CPU\ \(Single\ Core\):\d+)")
R23_REGX_MULTI = re.compile(
    r"(Cinebench R23\ /\ CPU\ \(Multi\ Core\):\d+\)|(Cinebench R23\ /\ CPU\ \(Multi Core\):\d+)|(Cinebench\ R23\ /\ Multi Core:\d+))|(Cinebench R23-Multi\ Core:\d+)|(Cinebench R23-CPU\ \(Multi\ Core\):\d+)")

def wifi_detail(networking_string):
    data = networking_string
    if data is not None:
        rows = data.split(',')
        for row in rows:
            if not ('Wi-Fi' in row or 'Wi-Fi'.lower() in row):
                continue
            wifi = row.split('(')
            module = ' ('.join(wifi[:len(wifi) - 1])
            wifi = wifi[-1].strip(')').strip('(')
            return module, wifi


def wifi(networking_string):
    data = wifi_detail(networking_string)
    return data[1] if data else None


def module(networking_string):
    data = wifi_detail(networking_string)
    return data[0] if data and len(data) > 1 else None


def bluetooth(networking_string):
    data = networking_string
    if data is not None:
        if 'bluetooth' in data.lower():
            blue = networking_string.split(',')
            for b in blue:
                if 'bluetooth' in b.lower():
                    return b
            return networking_string.split(',')[1]
        return None


def wan(networking_string):
    return None


def get_pl1(processor_string):
    return _value_parser('pl1', processor_string)


def get_pl2(processor_string):
    return _value_parser('pl2', processor_string)

def get_tdp(graphics_adapter_string):
    return _value_parser('tdp', graphics_adapter_string)

def get_battery_tech(battery_string):
    if not battery_string:
        return None
    elif 'Ion' in battery_string:
        return 'Lithium-Ion'
    elif 'Polymer' in battery_string:
        return 'Lithium-Polymer'
    else:
        return None

def check_side(text, side):
    return text.startswith(side) or text.startswith(side.lower())

def replace_side(text, side):
    return text.replace(f"{side} side:", "").replace(f"{side.lower()} side:", "").replace(f"{side} side", "").replace(f"{side.lower()} side", "").replace(f"{side}:", "").replace(f"{side.lower()}:", "").replace(side, "").replace(side.lower(), "")

def update_ports(ports, text):
    if text:
        # handle left side ports
        if check_side(text, "Left"):
            ports['port_left'] = replace_side(text, "Left")

        # handle right side ports
        if check_side(text, "Right"):
            ports['port_right'] = replace_side(text, "Right")

        # handle front side ports
        if check_side(text, "Front"):
            ports['port_front'] = replace_side(text, "Front")

        # handle rear/back side ports
        if check_side(text, "Rear"):
            ports['port_rear'] = replace_side(text, "Rear")
        elif check_side(text, "Back"):
            ports['port_rear'] = replace_side(text, "Back")

    return ports

def ports_info(connectivity, all_image_text):
    # # modified ports
    ports = {'port_left': "No ports", 'port_right': "No ports", 'port_front': "No ports", 'port_rear': "No ports"}
    if all_image_text:
        for text in all_image_text:
            if not connectivity:
                ports = update_ports(ports, text)
            else:
                if check_side(text, "Left") or check_side(text, "Right") or check_side(text, "Front") or check_side(text, "Rear") or check_side(text, "Back"):
                    ports = update_ports(ports, text)
                else:
                    if ports['port_right'] == 'No ports':
                        ports['port_right'] = 'Probably Right: ' + text
                    elif ports['port_left'] == 'No ports':
                        ports['port_left'] = 'Probably Left: ' + text
                    elif ports['port_front'] == 'No ports':
                        ports['port_front'] = 'Probably Front: ' + text
                    elif ports['port_rear'] == 'No ports':
                        ports['port_rear'] = 'Probably Rear: ' + text
                    
    return ports


def _value_parser(substring, value):
    if not value or substring not in value.lower():
        return None
    if "cell" in value.lower():
        return extract_string_value(substring, value.lower())
    values = value.split(",")
    for val in values:
        val = val.split("/")[0].strip()
        if substring not in val.lower():
            continue
        return re.search(r'[\d.]+', val).group()
    return None

def extract_string_value(substring, value):
    if substring == 'mah':
        c = re.findall(r'\d+\.\d+mah+', value)
        if c:
            return re.search(r'[\d.]+', c[0]).group()
        else:
            c = re.findall(r'\d+\.\d+ mah+', value)
            if c:
                return re.search(r'[\d.]+', c[0]).group()
            else:
                c = re.findall(r'\d+mah+', value)
                if c:
                    return re.search(r'[\d.]+', c[0]).group()
                else:
                    c = re.findall(r'\d+ mah+', value)
                    if c:
                        return re.search(r'[\d.]+', c[0]).group()
    elif substring == 'wh':
        d = re.findall(r'\d+\.\d+wh+', value)
        if d:
            return re.search(r'[\d.]+', d[0]).group()
        else:
            d = re.findall(r'\d+\.\d+ wh+', value)
            if d:
                return re.search(r'[\d.]+', d[0]).group()
            else:
                d = re.findall(r'\d+wh+', value)
                if d:
                    return re.search(r'[\d.]+', d[0]).group()
                else:
                    d = re.findall(r'\d+ wh+', value)
                    if d:
                        return re.search(r'[\d.]+', d[0]).group()
                    
def capacity_wh(battery_string):
    try:
        return int(float(_value_parser('wh', battery_string)))
    except (ValueError, TypeError):
        return None


def capacity_mah(battery_string):
    try:
        return int(float(_value_parser('mah', battery_string)))
    except (ValueError, TypeError):
        return None
    
def get_dimensions(item, _key):
        if not item:
            return None
        item = item.split("x")
        for i in item:
            if _key in i.lower():
                i.split("or")
                dimension = re.search(r"[\d.]+", i).group(0)
                return dimension if dimension else None
                        
def get_depth(item, _key):
    if not item:
        return None
    item = item.split("x")
    for i in item:
        for _k in _key:
            if _k in i.lower():
                i.split("or")
                dimension = re.search(r"[\d.]+", i).group(0)
    return dimension if dimension else None

def get_battery_type(battery_string, format=False, battery_series=True):
    cap_wh = capacity_wh(battery_string)
    cap_mah = capacity_mah(battery_string)
    if cap_wh and cap_mah:
        try:
            volt = cap_wh / (cap_mah / 1000)
            if 3 < volt < 4.5:
                n = 1
            elif 6 < volt < 9:
                n = 2
            elif 9 < volt < 13.5:
                n = 3
            elif 12 < volt < 18:
                n = 4
            else:
                return None
            m = round_up((cap_wh / n) / 20)
            if format:
                return f"{n}S{m}P"
            return n if battery_series else m
        except ZeroDivisionError:
            return None
    elif cap_wh and battery_series == True:
        if cap_wh >= 28:
            n = 3
        else:
            n = 2
        if format:
            return f"{n}S"
        return n
    
def get_cinebench(item, name):
    if not item:
        return None
    for i in item:
        if 'R23' in i:
            itm = i.split(',')
            if name == 'single' and 'single' in i.lower():
                itm = itm[0].split(':')
                return re.search(r'[\d.]+', itm[-1]).group()
            if name == 'multi' and 'multi' in i.lower():
                itm = itm[0].split(':')
                return re.search(r'[\d.]+', itm[-1]).group()
    return None
    
def cinebench_single_core(performance_string):
    if performance_string is None:
        return None
    match = R23_REGX_SINGLE.search(performance_string)
    if match:
        return match[0].split(':')[-1]
    return None

def cinebench_multi_core(performance_string):
    if performance_string is None:
        return None
    match = R23_REGX_MULTI.search(performance_string)
    if match:
        return match[0].split(':')[-1]
    return None

def get_additional_data(doc, table_name):
    
    target_div_with_tables = doc.xpath("//div[contains(@class, 'tx-nbc2fe-pi1')]//table[contains(@class, 'comparetable')]")
    target_table = None

    for table in target_div_with_tables:
        if table.xpath(f".//tr/td[contains(@class, 'subheader progname') and contains(normalize-space(text()), '{table_name}')]"):
            target_table = table
            break

    if target_table is not None:
        header_row = target_table.xpath(".//tr[2]/td")
    else:
        print(f'{table_name} table not present')
        return None
    
    target_column_index = None
    
    for index, header in enumerate(header_row):
        if not header.xpath("normalize-space(text())"):
            target_column_index = index + 1
            break

    if target_column_index:
        table_data = {}
        rows = target_table.xpath(".//tr[position()>1]")
        for row in rows:
            key = row.xpath(".//td[position()=1]/text()")[0].replace(' *', '').lower()
            value = row.xpath(f".//td[position()={target_column_index}]//div/text()")
            table_data[key] = value[0].strip() if value else None

        return table_data
    else:
        print(f"Target column not found in {table_name} Table")
        return None
    
def get_temp_limits(doc):
    def parse_temperature_data(temp_index, temp_type):
        
        temp_caption = None
        
        # create c_cover and d_cover with keys and None values
        c_cover = {f'{temp_type}_c_cover_{i+1}_{j+1}': None for i in range(3) for j in range(3)}
        d_cover = {f'{temp_type}_d_cover_{i+1}_{j+1}': None for i in range(3) for j in range(3)}

        try:
            parent_div = doc.xpath("//div[contains(@class, 'nbcheat_')]")[temp_index]
            text_data = parent_div.xpath('.//text()')
            try:
                temp_caption = text_data[-1]
            except Exception as e:
                print(f"Error extracting temp caption data: {e}")
            

            celsius_values = [element.replace(' °C', '').replace('°C', '') for element in text_data if element.strip().endswith('°C')]
            # update the c_cover and d_cover dictionaries with actual values
            for i in range(3):
                for j in range(3):
                    c_cover[f'{temp_type}_c_cover_{i+1}_{j+1}'] = celsius_values[i*3 + j]
                    d_cover[f'{temp_type}_d_cover_{i+1}_{j+1}'] = celsius_values[9 + i*3 + j]

        except Exception as e:
            print(e)

        return {
            "temp_caption": temp_caption,
            "c_cover": c_cover,
            "d_cover": d_cover
        }

    max_load = parse_temperature_data(0, "max_load")
    idle = parse_temperature_data(1, "idle")
    
    return max_load, idle

def get_prime95_score(doc, url):
    target_divs = doc.xpath("//div[contains(text(), 'Prime95') and contains(text(), 'Furmark')]")
    if target_divs:
        for target_div in target_divs:
            text = target_div.xpath('.//text()')
            href = target_div.xpath('.//a/@href')
            if text and href:
                info_div_text = ' '.join(text)
                if url in href[0]:
                    match = re.search(r'Ø(\d+(\.\d+)?)', info_div_text)
                    if match:
                        score = match.group(1)
                        return score
    else:
        return None
    