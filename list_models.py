import os
import requests
from dotenv import load_dotenv

# Load GROQ_API_KEY from the .env file
load_dotenv()
api_key = os.environ.get("GROQ_API_KEY")

# Ask Groq: "which models can I use?"
url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get(url, headers=headers)

# Print each model's ID
for model in response.json()["data"]:
    print(model["id"])