import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MAX_HISTORY = int(os.getenv("MAX_HISTORY", 10))
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", 3))
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", 7200))
REFRESH_MENU_PERIOD = int(os.getenv("REFRESH_MENU_PERIOD", 43200))