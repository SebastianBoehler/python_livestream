# integrate grok from xAI, should excel at latest news bc of tweet search

# usage from xAi docs
import os
import requests

url = "https://api.x.ai/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('XAI_API_KEY')}"
}
payload = {
    "messages": [
        {
            "role": "user",
            "content": "What is the most viral meme in 2022?"
        }
    ],
    "search_parameters": {
        "mode": "auto",
        "from_date": "2022-01-01",
        "to_date": "2022-12-31",
        "sources": [{ "type": "web", "country": "us"}, {"type": "x", "x_handles": ["elonmusk", "jack", "satoshi", ""]}, { "type": "news", "excluded_websites": ["bbc.co.uk"] }]
    },
    "model": "grok-3-latest"
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
