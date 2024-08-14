import requests
from decouple import config

api_key = config('AZURE_OPENAI_API_KEY')
api_version = config('AZURE_OPENAI_API_VERSION')
gpt_link = config('AZURE_OPENAI_ENDPOINT')
deployment_id = config('AZURE_OPENAI_GPT_DEPLOYMENT_ID')

def gpt_html_extract(text_strings, system_prompt):
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    payload = {
        "messages": [
            {
            "role": "system",
            "content":  system_prompt
            },
            {
            "role": "user",
            "content": text_strings
            }
        ],
        "temperature": 0.8,
        "response_format": {"type": "json_object"}
    }

    try:
        url = f"{gpt_link}/openai/deployments/{deployment_id}/chat/completions?api-version={api_version}"
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error during GPT extraction: {e}")
        return None
