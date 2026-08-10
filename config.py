from dotenv import load_dotenv
import os

load_dotenv()

BASE_PATH = os.getenv('BASE_PATH', '')

PREVIEW_MODE = False
OUTPUT_PATH = f"{BASE_PATH}/outputs"