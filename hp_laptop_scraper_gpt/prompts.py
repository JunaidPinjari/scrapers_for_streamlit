def create_combined_prompt():    
    json_structure = """
    {
        "PROCESSOR_BRAND": "",
        "PROCESSOR_FAMILY": "",
        "PROCESSOR_GENERATION": "",
        "CPU_SPEED": "",
        "GRAPHICS_BRAND": "",
        "GRAPHICS_FAMILY": "",
        "GRAPHICS_RAM": "",
        "GRAPHICS_RAM_TYPE": "",
        "DISPLAY_SIZE": "",
        "DISPLAY_RESOLUTION": "",
        "DISPLAY_REFRESH": "",
        "DISPLAY_OTHERS": "",
        "RAM_MEMORY": "",
        "RAM_TYPE": "",
        "RAM_SPEED": "",
        "STORAGE_SIZE": "",
        "STORAGE_TYPE": "",
        "STORAGE_OTHERS": ""
    }
    """

    example_input_1 = """
    processor: Intel Core Ultra 7 165H (up to 5.0 GHz with Intel Turbo Boost Technology, 24 MB L3 cache, 14 cores, 22 threads) [6,7]
    memory: 64 GB DDR5-5600 MHz RAM (2 x 32 GB)
    memory slots: 2 SODIMM; supports dual channel
    internal drive: 1 TB PCIe Gen4 NVMe TLC M.2 SSD
    display: 16" diagonal, WQXGA (2560 x 1600), IPS, anti-glare, Low Blue Light, 400 nits, 100% sRGB [21,22,23,24]
    graphics: Integrated: Intel Arc Graphics
    Discrete: NVIDIA RTX A1000 Laptop GPU (6 GB GDDR6 dedicated)
    Weight: 3.13 lb
    """
    
    example_output_1 = """
    {
        "PROCESSOR_BRAND": "Intel",
        "PROCESSOR_FAMILY": "Core Ultra 7",
        "PROCESSOR_GENERATION": "165H",
        "CPU_SPEED": "5.0 GHz",
        "CPU_CACHE": "24 MB L3",
        "CPU_CORES": "14",
        "CPU_THREADS": "22",
        "GRAPHICS_BRAND": "Intel",
        "GRAPHICS_FAMILY": "Arc Graphics",
        "GRAPHICS_RAM": "6 GB",
        "GRAPHICS_RAM_TYPE": "GDDR6",
        "DISPLAY_SIZE": "16\"",
        "DISPLAY_RESOLUTION": "2560 x 1600",
        "DISPLAY_REFRESH": "None",
        "DISPLAY_OTHERS": "diagonal WQXGA IPS anti-glare Low Blue Light 400 nits 100% sRGB",
        "RAM_MEMORY": "64 GB",
        "RAM_TYPE": "DDR5",
        "RAM_SPEED": "5600 MHz",
        "STORAGE_SIZE": "1 TB",
        "STORAGE_TYPE": "SSD",
        "STORAGE_OTHERS": "PCIe Gen4 NVMe TLC M.2",
        "WEIGHT_KG": "1.42"
    }
    """
    
    example_input_2 = """
        Processor: 12th Gen Intel® Core™ i3-1215U (10 MB cache, 6 cores, 20 threads, up to 4.40 GHz Turbo)
        Graphics Card: NVIDIA® GeForce RTX™ 4090, 24 GB GDDR6X
        Display: 15.6", FHD 1920x1080, 120Hz, WVA, IPS, Non-Touch, Anti-Glare, 250 nit, Narrow Border, LED-Backlit
        Memory: 64 GB: 2 x 32 GB, DDR5, 5200 MT/s
        Storage: 512 GB, M.2, PCIe NVMe, SSD
        Weight: 3.99 lb
    """
    example_output_2 = """
    {
        "PROCESSOR_BRAND": "Intel",
        "PROCESSOR_FAMILY": "Core i3",
        "PROCESSOR_GENERATION": "12th Gen (1215U)",
        "CPU_SPEED": "4.40 GHz",
        "CPU_CACHE": "10 MB",
        "CPU_CORES": "6",
        "CPU_THREADS": "20",
        "GRAPHICS_BRAND": "NVIDIA",
        "GRAPHICS_FAMILY": "GeForce RTX 4090",
        "GRAPHICS_RAM": "24 GB",
        "GRAPHICS_RAM_TYPE": "GDDR6X",
        "DISPLAY_SIZE": "15.6\"",
        "DISPLAY_RESOLUTION": "1920x1080",
        "DISPLAY_REFRESH_RATE": "120Hz",
        "DISPLAY_OTHERS": "WVA, IPS, Non-Touch, Anti-Glare, 250 nit, Narrow Border, LED-Backlit",
        "RAM_MEMORY": "64 GB",
        "RAM_TYPE": "DDR5",
        "RAM_SPEED": "5200 MT/s",
        "STORAGE_SIZE": "512 GB",
        "STORAGE_TYPE": "SSD",
        "STORAGE_OTHERS": "M.2, PCIe NVMe",
        "WEIGHT_KG": "1.81",
    }
    """
    prompt = f"""
    You are designed to extract specific information from given text and output it in a structured JSON format. The text will contain various specifications and measurements. Follow these guidelines to ensure accuracy:

        1. Extract only the required details as specified in the JSON format.
        2. Ignore irrelevant information or details that do not match the specified variables.
        3. Make sure you get processor family and generation correct according to the examples.
        4. If a required variable is missing, return "None" for that field.
        5. Return the results in the following JSON format: {json_structure}
        6. Be consistent and precise in extracting and formatting the information.

    Example input:
    {example_input_1}

    Example output:
    {example_output_1}

    Example input 2:
    {example_input_2}

    Example output 2:
    {example_output_2}
    """

    return prompt