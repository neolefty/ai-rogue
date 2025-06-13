import os
import requests
from dotenv import load_dotenv

class OpenAIClient:
    """Simple wrapper around the OpenAI HTTP API"""
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_image(self, prompt, size="256x256", quality="standard"):
        try:
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=self.headers,
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                    "quality": quality,
                    "response_format": "url"
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {str(e)}")
            print(f"Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            raise

    def generate_chat_completion(self, messages):
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": "gpt-3.5-turbo",
                "messages": messages
            }
        )
        response.raise_for_status()
        return response.json()

client = OpenAIClient()
