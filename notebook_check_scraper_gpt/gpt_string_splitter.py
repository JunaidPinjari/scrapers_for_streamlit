import json
import requests
from decouple import config

RETRY_COUNT = 2

def make_request(headers, payload):
    url = f"{config('AZURE_OPENAI_ENDPOINT')}/openai/deployments/{config('AZURE_OPENAI_DEPLOYMENT_MODEL_ID')}/chat/completions?api-version={config('AZURE_OPENAI_API_VERSION')}"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_json = response.json()['choices'][0]['message']['content']
    return json.loads(response_json)

def gpt_html_extract(text_strings):
    headers = {
        "Content-Type": "application/json",
        "api-key": config("AZURE_OPENAI_API_KEY")
    }

    system_prompt = """
        You are designed to extract specific information from given text and output it in a structured JSON format. The text will contain various specifications and measurements. Follow these guidelines to ensure accuracy:

        1. Extract only the required details: screen size, screen resolution, power supply temperature (in Celsius), and room temperature (in Celsius), availability and Number of USB type C port in left, right, rear and front side.
        2. If the USB C port is available on the side, then return the number of USB-C ports available on that side. If not, return "None".
        3. Ignore irrelevant information or details that do not match the specified variables.
        4. If a required variable is missing, return "None" for that field.
        5. Ensure all temperatures are converted to Celsius if provided in Fahrenheit.
        6. Return the results in the following JSON format:
        {
            "screen_size": "",
            "screen_resolution": "",
            "max_load_power_supply_temperature": "",
            "max_load_room_temperature": "",
            "idle_power_supply_temperature": "",
            "idle_room_temperature": "",
            "type_c_ports_left": "",
            "type_c_ports_right": "",
            "type_c_ports_rear": "",
            "type_c_ports_front": "",
        }
        7. Maintain the same units as provided in the input for screen size and resolution.
        8. Be consistent and precise in extracting and formatting the information.

        Example input:
        "Display: 16.00 inch 16:10, 2880 x 1800 pixel 212 PPI, Capacitive, native pen support, ATNA60CL06-0, OLED, glossy: yes, 120 Hz
        Max_Load Power Supply (max.): 51.3 Â°C = 124 F
        Max_Load Room Temperature: 22 Â°C = 72 F
        Left: Probably Left: HDMI 2.1, 2x USB-C 4.0 (40 Gbit/s, DisplayPort ALT mode 1.4, microSD card reader, 3.5-mm audio
        Right: No Ports
        "

        Example output:
        {
            "screen_size": "16.00",
            "screen_resolution": "2880 x 1800",
            "max_load_power_supply_temperature": "51.3",
            "max_load_room_temperature": "22",
            "idle_power_supply_temperature": "None",
            "idle_room_temperature": "None",
            "type_c_ports_left": "2",
            "type_c_ports_right": "None",
            "type_c_ports_rear": "None",
            "type_c_ports_front": "None"
        }

        If temperatures are provided only in Fahrenheit, convert them to Celsius using the formula: (F - 32) * 5/9 and include the converted value in the JSON output.
    """

    payload = {
        "messages": [
            {
            "role": "system",
            "content":  system_prompt
            },
            {
            "role": "user",
            "content": f"{text_strings}"
            }
        ],
        "temperature": 0.8,
        "response_format": {"type": "json_object"}
    }

    for attempt in range(RETRY_COUNT + 1):
        try:
            return make_request(headers, payload)
        except Exception as e:
            print(f"Error during GPT extraction (attempt {attempt + 1}): {e}")
            if attempt < RETRY_COUNT:
                print("Retrying...")
            else:
                return None