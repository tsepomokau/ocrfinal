import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API settings
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# OpenAI API settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# File processing settings
TEMP_FOLDER = os.getenv("TEMP_FOLDER", "./temp")
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Max file size (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file types
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "tif"}

# OCR settings
DEFAULT_OCR_LANGUAGE = "eng"
OCR_DPI = 300