def create_combined_prompt():
    json_structure = """
    {
        "PROCESSOR_BRAND": "",
        "PROCESSOR_FAMILY": "",
        "PROCESSOR_GENERATION": "",
        "CPU_SPEED": "",
        "CPU_CACHE": "",
        "CPU_CORES": "",
        "CPU_THREADS": "",
        "GRAPHICS_BRAND": "",
        "GRAPHICS_FAMILY": "",
        "GRAPHICS_RAM": "",
        "GRAPHICS_RAM_TYPE": "",
        "DISPLAY_SIZE": "",
        "DISPLAY_RESOLUTION": "",
        "DISPLAY_REFRESH_RATE": "",
        "DISPLAY_OTHERS": "",
        "RAM_MEMORY": "",
        "RAM_TYPE": "",
        "RAM_SPEED": "",
        "STORAGE_SIZE": "",
        "STORAGE_TYPE": "",
        "STORAGE_OTHERS": "",
        "HEIGHT": "",
        "WIDTH": "",
        "DEPTH": "",
        "WEIGHT": "",
    }
    """

    example_input_1 = """
        Processor: Snapdragon X Plus X1P-64-100 (10 cores up to 3.4GHz, 45 TOPS NPU)
        Graphics Card: Integrated QualcommÂ Adrenoâ¢ GPUÂ, SnapdragonÂ X Plus X1P-64-100, 10 cores, 16GB LPDDR5x Memory
        Display: Laptop 14.0" QHD+ 2560 x 1600, 30-120Hz, IPS, AG Touch, ComfortView+, SLP, 400 nits, FHD IR Cam, WLAN
        Memory: 16 GB, LPDDR5x, 8448 MT/s, onboard
        Storage: 512 GB, M.2 2230, TLC PCIe Gen 4 NVMe, SSD
        Dimensions & Weight: Height: 0.60 in. (15.30 mm) for computers shipped with FHD+ or QHD+ display, Height: 0.58 in. (14.80 mm) for computers shipped with OLED display, Width: 11.62 in. (295.30 mm), Depth: 7.84 in. (199.10 mm), Starting weight: 2.62 lb (1.19 kg) for computers shipped with FHD+ or QHD+ display, Starting weight: 2.60 lb (1.17 kg) for computers shipped with OLED display
    """
    
    example_output_1 = """
    {
        "PROCESSOR_BRAND": "Snapdragon",
        "PROCESSOR_FAMILY": "X Plus",
        "PROCESSOR_GENERATION": "X1P-64-100",
        "CPU_SPEED": "3.4 GHz",
        "CPU_CACHE": "None",
        "CPU_CORES": "10",
        "CPU_THREADS": "None",
        "GRAPHICS_BRAND": "Qualcomm",
        "GRAPHICS_FAMILY": "Adreno",
        "GRAPHICS_RAM": "16 GB",
        "GRAPHICS_RAM_TYPE": "LPDDR5x",
        "DISPLAY_SIZE": "14.0\"",
        "DISPLAY_RESOLUTION": "2560x1600",
        "DISPLAY_REFRESH_RATE": "30-120Hz",
        "DISPLAY_OTHERS": "IPS, AG Touch, ComfortView+, SLP, 400 nits, FHD IR Cam, WLAN",
        "RAM_MEMORY": "16 GB",
        "RAM_TYPE": "LPDDR5x",
        "RAM_SPEED": "8448 MT/s",
        "STORAGE_SIZE": "512 GB",
        "STORAGE_TYPE": "SSD",
        "STORAGE_OTHERS": "M.2 2230, TLC PCIe Gen 4 NVMe,"
        "HEIGHT": "0.58 to 0.60",
        "WIDTH": "11.62",
        "DEPTH": "7.84",
        "WEIGHT_KG": "1.17 to 1.19",
    }
    """

    
    example_input_2 = """
        Processor: 12th Gen Intel® Core™ i3-1215U (10 MB cache, 6 cores, 20 threads, up to 4.40 GHz Turbo)
        Graphics Card: NVIDIA® GeForce RTX™ 4090, 24 GB GDDR6X
        Display: 15.6", FHD 1920x1080, 120Hz, WVA, IPS, Non-Touch, Anti-Glare, 250 nit, Narrow Border, LED-Backlit
        Memory: 64 GB: 2 x 32 GB, DDR5, 5200 MT/s
        Storage: 512 GB, M.2, PCIe NVMe, SSD
        Dimensions & Weight: Depth: 9.40 in. (239.70 mm) , Width: 14.10 in. (359.00 mm) , Height: 0.71 in. (18.10 mm) , Starting weight: 1.81 kg (3.99 lb)
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
        "HEIGHT": "0.71",
        "WIDTH": "14.10",
        "DEPTH": "9.40",
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
