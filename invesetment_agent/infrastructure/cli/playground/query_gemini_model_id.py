import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

env_path: Path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
# Initialize the client
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))


# check the price for each model here: https://costgoat.com/pricing/gemini-api
# List all available models
for model in client.models.list():
    print(model.name)
