from dotenv import load_dotenv
import os

load_dotenv()

BASE_PATH = os.getenv('BASE_PATH', '')

CONTENT_LIBRARIES=[
    {'LibName':'Movies','ContentType':'movies'},
    {'LibName':'TV Shows','ContentType':'tv'},
]

PREVIEW_MODE = False
OUTPUT_PATH = f"{BASE_PATH}/outputs"

FPS = 24
SCREENSAVER_DURATION = 10

LOGO_DRIFT_DISTANCE = 60


LOGO_HEIGHT    = 287
LOGO_MAX_WIDTH = 880
LOGO_OFFSET_X = 50
LOGO_OFFSET_Y = 100

ZOOM_END       = 1.1