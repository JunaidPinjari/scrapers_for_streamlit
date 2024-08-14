import requests
from fake_useragent import UserAgent

ua = UserAgent()
## Returns original url appended with archive url and timestamp
def get_archive_urls(old_url):
    
    url = f'https://web.archive.org/__wb/sparkline?output=json&url={old_url}&collection=web'
    headers = {
        'referer': f'https://web.archive.org/web/20240000000000*/{old_url}',
        'User-Agent': ua.random,
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        timestamp_first = data.get('first_ts', None)
        timestamp_last = data.get('last_ts', None)
        timestamp_first_url = None
        timestamp_last_url = None

        if timestamp_first:  
            timestamp_first_url = f'https://web.archive.org/web/{timestamp_first}/{old_url}'
        if timestamp_last:
            timestamp_last_url = f'https://web.archive.org/web/{timestamp_last}/{old_url}'
        
        return timestamp_first_url, timestamp_last_url
    
    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return False, False 