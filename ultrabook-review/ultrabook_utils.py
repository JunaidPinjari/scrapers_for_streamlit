import datetime
import re
from math import ceil as round_up
import uuid
from lxml import etree

R23_REGX_SINGLE = R23_REGX_SINGLE = re.compile(
    r"\d+|(Cinebench R23\ /\ Single\ Core:\d+)|Cinebench R23-Single\ Core:\d+|(Cinebench R23-CPU\ \(Single\ Core\):\d+)")
R23_REGX_MULTI = re.compile(
    r"(Cinebench R23\ /\ CPU\ \(Multi\ Core\):\d+\)|(Cinebench R23\ /\ CPU\ \(Multi Core\):\d+)|(Cinebench\ R23\ /\ Multi Core:\d+))|(Cinebench R23-Multi\ Core:\d+)|(Cinebench R23-CPU\ \(Multi\ Core\):\d+)")

def get_hash_id():
    # hash_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]+str(uuid.uuid4().hex)[:15]
    hash_id = uuid.uuid4().hex
    return hash_id

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
        return re.search('[\d.]+', val).group()
    return None

def extract_string_value(substring, value):
    if substring == 'mah':
        c = re.findall('\d+\.\d+mah+', value)
        if c:
            return re.search('[\d.]+', c[0]).group()
        else:
            c = re.findall('\d+\.\d+ mah+', value)
            if c:
                return re.search('[\d.]+', c[0]).group()
            else:
                c = re.findall('\d+mah+', value)
                if c:
                    return re.search('[\d.]+', c[0]).group()
                else:
                    c = re.findall('\d+ mah+', value)
                    if c:
                        return re.search('[\d.]+', c[0]).group()
    elif substring == 'wh':
        d = re.findall('\d+\.\d+wh+', value)
        if d:
            return re.search('[\d.]+', d[0]).group()
        else:
            d = re.findall('\d+\.\d+ wh+', value)
            if d:
                return re.search('[\d.]+', d[0]).group()
            else:
                d = re.findall('\d+wh+', value)
                if d:
                    return re.search('[\d.]+', d[0]).group()
                else:
                    d = re.findall('\d+ wh+', value)
                    if d:
                        return re.search('[\d.]+', d[0]).group()
                    
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
                            dimension = re.search("[\d.]+", i).group(0)
                            return dimension if dimension else None
                        
def get_depth(item, _key):
    if not item:
        return None
    item = item.split("x")
    for i in item:
        for _k in _key:
            if _k in i.lower():
                i.split("or")
                dimension = re.search("[\d.]+", i).group(0)
    return dimension if dimension else None

def battery(battery_string, format=False, battery_series=True):
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
    # print(item)
    # for i in item:
    #     # print(i)
    #     # print("="*40)
    #     if 'R23' in i:  
    #         print("found R23")
    itm = item.split(":", 1)[-1].split(',')
    if name == 'single':
        if 'single' in itm[-1].lower():
            return re.search('[\d.]+', itm[-1]).group()
    if name == 'multi':
        return re.search('[\d.]+', itm[0]).group()
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

def get_table_data(table_element):
    table_data = []
    table_rows = table_element.xpath("tbody/tr")
    for row in table_rows:
        cells_data = row.xpath('td//text()')
        table_data.append(cells_data)
    return table_data

def get_ul_data(ul_element):
    ul_data = []
    ul_rows = ul_element.xpath(".//li")
    for row in ul_rows:
        cells_data = ''.join(row.xpath('.//text()'))
        ul_data.append(cells_data)
    return ul_data

def get_section_key(section_string):
    key = section_string.lower().replace(",", "").replace(" ", "_")
    return key
    