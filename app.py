from datetime import datetime
import logging
import os
import random
from typing import Literal

import numpy as np
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv
from PIL import Image
from moviepy import VideoClip
from db_functions import insert_record
from plex import get_unwatched_movies, get_unwatched_tvshows

logging.basicConfig(level=logging.DEBUG)

# Typing Literals
MediaType = Literal["tv", "movie"]
Assets = Literal["logo", "background", "both"]

load_dotenv()

FANARTTV_API_KEY = os.environ["FANARTTV_API_KEY"]
TMDB_API_KEY = os.environ["TMDB_API_KEY"]


def download_image(image_url:str, filename:str, save_dir:str='artwork') -> str | None :
    try:
        file_extension = image_url.split('.')[-1]
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{filename}.{file_extension}")
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        return save_path
    except Exception:
        return None


def resize_background_to_1080p(image_path: str) -> str:
    """Resize background image to 1920x1080 and save."""
    target_size = (1920, 1080)
    image = Image.open(image_path).convert("RGBA")

    # Calculate aspect ratio to maintain it
    img_ratio = image.width / image.height
    target_ratio = target_size[0] / target_size[1]

    if img_ratio > target_ratio:
        # Image is wider, fit to height
        new_height = target_size[1]
        new_width = int(new_height * img_ratio)
    else:
        # Image is taller, fit to width
        new_width = target_size[0]
        new_height = int(new_width / img_ratio)

    # Resize image
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Create new image with target dimensions and paste resized image centered
    final_image = Image.new("RGBA", target_size, (0, 0, 0, 0))
    offset_x = (target_size[0] - new_width) // 2
    offset_y = (target_size[1] - new_height) // 2
    final_image.paste(resized, (offset_x, offset_y), resized)

    # Save over the original file
    final_image.save(image_path, "PNG")
    return image_path




def get_fanarttv_media_artwork(media_type: MediaType, media_id: int, assets_to_fetch: Assets = 'both') -> dict | None:

    if not FANARTTV_API_KEY:
        logging.error("FANARTTV_API_KEY not set")
        return None

    saved_images = {}
    # Fanart uses 'movies' rather than 'movie'
    api_media_type = 'movies' if media_type == 'movie' else media_type
    url = f"https://webservice.fanart.tv/v3.2/{api_media_type}/{media_id}"
    params = {"api_key": FANARTTV_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"FanartTV API error for {media_type}/{media_id}: {e}")
        return None

    data = response.json()

    # Logo
    if assets_to_fetch in ['logo', 'both']:
        if api_media_type == 'tv':
            logo_art = [image for image in data.get('hdtvlogo', []) if image['lang'] == 'en']
        else:
            logo_art = [image for image in data.get('hdmovielogo', []) if image['lang'] == 'en']

        if logo_art:
            found_logo = download_image(logo_art[0]['url'], f"{media_id}_logo")
            if found_logo:
                saved_images['logo'] = found_logo

    # Background
    if assets_to_fetch in ['background', 'both']:
        if api_media_type == 'tv':
            background_art = data.get('showbackground', [])
        else:
            background_art = data.get('moviebackground', [])

        if background_art:
            background = random.choice(background_art)
            found_background = download_image(background['url'], f"{media_id}_background")
            if found_background:
                saved_images['background'] = found_background

    return saved_images if saved_images else None
                    
def make_static_background(background_path:str, logo_path:str, output_filename:str, margin:int=20):
    # Open the images and ensure they support transparency
    background_path = resize_background_to_1080p(background_path)
    background = Image.open(background_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    # Calculate position for bottom-left placement with a margin, 5% higher
    x = margin
    y = int(background.height - logo.height - margin * 1.05)

    # Paste logo onto background, using logo's alpha channel as the mask
    background.paste(logo, (x, y), logo)

    # Save as PNG to preserve transparency
    background.save(output_filename, "PNG")
    print(f"Saved combined image to {output_filename}")

def ease_in_out(t):
    """Smooth acceleration/deceleration curve instead of linear motion."""
    return 0.5 - 0.5 * np.cos(np.pi * t)

def make_screensaver(
    background_path,
    logo_path,
    output_filename,
    duration=10,
    fps=24,
    zoom_end=1.1,       # subtle background zoom
    logo_drift_px=50,    # bigger drift = smoother-looking motion at integer pixels
    margin=20
):
    background_path = resize_background_to_1080p(background_path)
    background = Image.open(background_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    bg_w, bg_h = background.size
    logo_h = logo.height

    def make_frame(t):
        progress = ease_in_out(t / duration)
        zoom = 1.0 + (zoom_end - 1.0) * progress

        # --- Background zoom: single-step affine transform (sub-pixel accurate) ---
        src_w = bg_w / zoom
        src_h = bg_h / zoom
        src_left = (bg_w - src_w) / 2
        src_top = (bg_h - src_h) / 2

        a = src_w / bg_w
        d = src_h / bg_h
        cropped_bg = background.transform(
            (bg_w, bg_h),
            Image.AFFINE, # type: ignore
            (a, 0, src_left, 0, d, src_top),
            resample=Image.BICUBIC # type: ignore
        )

        frame = cropped_bg.copy()

        # --- Logo drift: simple integer positioning, no sub-pixel needed ---
        x = margin + round(logo_drift_px * progress)
        y = int(bg_h - logo_h - margin * 1.05)
        frame.paste(logo, (x, y), logo)

        return np.array(frame.convert("RGB"))

    clip = VideoClip(make_frame, duration=duration).with_fps(fps)

    clip.write_videofile( # type: ignore
        output_filename,
        codec="libx264",
        fps=fps,
        audio=False,
        ffmpeg_params=["-crf", "18"]
    )
    return output_filename

def get_tmdb_media_artwork(media_type: MediaType, media_id: int, assets_to_fetch: Assets = 'both') -> dict | None:
    
    if not TMDB_API_KEY:
        logging.error("TMDB_API_KEY not set")
        return None
    
    saved_images = {}
    url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/images"
    params = {"api_key": TMDB_API_KEY}
    TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"TMDB API error for {media_type}/{media_id}: {e}")
        return None

    data = response.json()
    
    # Logo
    if assets_to_fetch in ['logo', 'both']:
        logo_art = sorted(
            [img for img in data.get('logos', []) if img.get('iso_639_1') in ('en', None)],
            key=lambda x: x.get('vote_average', 0),
            reverse=True
        )
        if logo_art:
            found_logo = download_image(TMDB_IMAGE_BASE_URL + logo_art[0]['file_path'], f"{media_id}_logo")
            if found_logo:
                saved_images['logo'] = found_logo
    
    # Background
    if assets_to_fetch in ['background', 'both']:
        # iso_639_1 is language fields, metadata without it should be textless by default
        background_art = sorted(
            [img for img in data.get('backdrops', []) if img.get('iso_639_1') is None],
            key=lambda x: x.get('vote_average', 0),
            reverse=True
        )
        if background_art:
            found_background = download_image(TMDB_IMAGE_BASE_URL + background_art[0]['file_path'], f"{media_id}_background")
            if found_background:
                saved_images['background'] = found_background
    
    return saved_images if saved_images else None  
    
def fetch_assets_and_make_screensaver(media_name, category, tmdb_id, tvdb_id, current=1, total=1):
    """
    Fetch media artwork from TMDB, fallback to FanartTV if needed, then create screensaver.

    Args:
        media_name: Name of the media
        category: 'tv' or 'movie'
        tmdb_id: TheMovieDB ID
        tvdb_id: TheTVDB ID (for TV shows, used with FanartTV)
        current: Current item number in batch
        total: Total items in batch
    """
    # Try to get both artworks from TMDB first
    artwork_dict = get_tmdb_media_artwork(category, tmdb_id, 'both')

    if not artwork_dict:
        artwork_dict = {}

    print(f"TMDB artwork: {artwork_dict}")

    # Verify we have both required assets
    if not artwork_dict.get('logo') or not artwork_dict.get('background'):
        logging.error(f"Could not fetch complete artwork for {tmdb_id}")
        return None

    # Check file extensions: logo must be .png and background must be .jpg
    logo_ext = artwork_dict['logo'].split('.')[-1].lower()
    bg_ext = artwork_dict['background'].split('.')[-1].lower()

    if logo_ext != 'png' or bg_ext != 'jpg':
        logging.warning(f"Skipping {media_name}: logo is .{logo_ext}, background is .{bg_ext} (need .png and .jpg)")
        return None

    # Create screensaver
    output_filename = f"{tmdb_id}_screensaver.mp4"
    make_screensaver(
        background_path=artwork_dict['background'],
        logo_path=artwork_dict['logo'],
        output_filename=output_filename
    )

    print(f"Creating wallpapers - {current}/{total} created")


unwatched_tv_shows = get_unwatched_tvshows()
total_shows = len(unwatched_tv_shows)
start_time = datetime.now()
# for show in unwatched_tv_shows:
#     print (show)
for movie in get_unwatched_movies():
    print (movie)

# for idx, show in enumerate(unwatched_tv_shows, 1):
#     if show['tmdb']:
#         fetch_assets_and_make_screensaver(show['title'], 'tv', show['tmdb'], 555, idx, total_shows)

#         elapsed = (datetime.now() - start_time).total_seconds()
#         if idx < total_shows:
#             avg_time_per_item = elapsed / idx
#             remaining_items = total_shows - idx
#             estimated_remaining = avg_time_per_item * remaining_items
#             print(f"Elapsed: {int(elapsed // 60)}m - Estimated time to finish: {int(estimated_remaining // 60)} minutes\n")

fetch_assets_and_make_screensaver('hello','movie',687163,555)
fetch_assets_and_make_screensaver('hello','movie',1226863,555)
fetch_assets_and_make_screensaver('hello','movie',1368166,555)
fetch_assets_and_make_screensaver('hello','movie',1087822,555)
fetch_assets_and_make_screensaver('hello','movie',724495,555)
fetch_assets_and_make_screensaver('hello','movie',1430077,555)
fetch_assets_and_make_screensaver('hello','movie',1266127,555)
