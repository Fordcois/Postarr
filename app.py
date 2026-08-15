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
from db_functions import upsert_record,update_record,remove_record,get_record
from plex import get_unwatched_media
from pathlib import Path

from config import ZOOM_END,SCREENSAVER_DURATION,FPS,LOGO_HEIGHT,LOGO_MAX_WIDTH,LOGO_OFFSET_X,LOGO_OFFSET_Y,PREVIEW_MODE,OUTPUT_PATH,LOGO_DRIFT_DISTANCE

logging.basicConfig(level=logging.WARNING)

# Typing Literals
MediaType = Literal["tv", "movie"]
Assets = Literal["logo", "background", "both"]

load_dotenv()

FANARTTV_API_KEY = os.environ["FANARTTV_API_KEY"]
TMDB_API_KEY = os.environ["TMDB_API_KEY"]


def download_image(image_url: str, filename: str, save_dir: str = 'artwork', is_background: bool = False,is_logo:bool=False) -> str | None:
    try:
        file_extension = image_url.split('.')[-1]
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{filename}.{file_extension}")
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)

        if is_background:
            # Resize background to 1080p immediately after download
            save_path = resize_image(save_path)
        if is_logo:
            save_path= resize_image(save_path, height=LOGO_HEIGHT, max_width=LOGO_MAX_WIDTH, preserve_canvas=False)

        return save_path
    except Exception:
        return None


def resize_image(image_path: str, width: int = 1920, height: int = 1080, preserve_canvas: bool = True, max_width: int | None = None) -> str:
    """Resize image and save as a PNG

    Args:
        preserve_canvas: If True, creates canvas and centers image (for backgrounds)
                        If False, just scales image (for logos)
        max_width: Maximum width constraint for logos (applies only when preserve_canvas=False)
    """
    image = Image.open(image_path).convert("RGBA")
    img_ratio = image.width / image.height

    if preserve_canvas:
        # Original behavior - fit into canvas
        target_ratio = width / height

        if img_ratio > target_ratio:
            new_height = height
            new_width = int(new_height * img_ratio)
        else:
            new_width = width
            new_height = int(new_width / img_ratio)

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        final_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        offset_x = (width - new_width) // 2
        offset_y = (height - new_height) // 2
        final_image.paste(resized, (offset_x, offset_y), resized)
        final_image.save(image_path, "PNG")
    else:
        # Logo mode - scale by height, but constrain width if it exceeds max_width
        new_height = height
        new_width = int(new_height * img_ratio)

        # If width exceeds max_width, scale by width instead
        if max_width and new_width > max_width:
            new_width = max_width
            new_height = int(new_width / img_ratio)

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized.save(image_path, "PNG")

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
            found_logo = download_image(logo_art[0]['url'], f"{media_id}_logo",is_logo=True)
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
            found_background = download_image(background['url'], f"{media_id}_background",is_background=True)
            if found_background:
                saved_images['background'] = found_background

    return saved_images if saved_images else None
                    
def ease_in_out(t):
    """Smooth acceleration/deceleration curve instead of linear motion."""
    return 0.5 - 0.5 * np.cos(np.pi * t)

def make_screensaver(
    background_path,
    logo_path,
    output_filename,
    duration=SCREENSAVER_DURATION,
    fps=FPS,
    zoom_end=ZOOM_END,
    logo_drift_px=LOGO_DRIFT_DISTANCE,
    preview=False,
    logo_offset_x=LOGO_OFFSET_X,
    logo_offset_y=LOGO_OFFSET_Y
):
    background = Image.open(background_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    bg_w, bg_h = background.size
    logo_h = logo.height

    def make_frame(t):
        progress = ease_in_out(t / duration)
        zoom = 1.0 + (zoom_end - 1.0) * progress

        src_w = bg_w / zoom
        src_h = bg_h / zoom
        src_left = (bg_w - src_w) / 2
        src_top = (bg_h - src_h) / 2

        a = src_w / bg_w
        d = src_h / bg_h
        cropped_bg = background.transform(
            (bg_w, bg_h),
            Image.AFFINE,
            (a, 0, src_left, 0, d, src_top),
            resample=Image.BICUBIC
        )

        frame = cropped_bg.copy()

        x = logo_offset_x + logo_drift_px * (t / duration)
        y = bg_h - logo_h - logo_offset_y
        frame.paste(logo, (int(x), int(y)), logo)

        return np.array(frame.convert("RGB"))

    if preview:
        # Just save the first frame as PNG
        frame = make_frame(0)
        img = Image.fromarray(frame)
        preview_filename = output_filename.replace('.mp4', '_preview.png')
        img.save(preview_filename, "PNG")
        print(f"Saved preview to {preview_filename}")
        return preview_filename
    
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
    
    images = {}
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
            [img for img in data.get('logos', []) 
            if img.get('iso_639_1') in ('en', None) and img['file_path'].lower().endswith('.png')],
            key=lambda x: x.get('vote_average', 0),
            reverse=True
        )
        if logo_art:
            logo_url = TMDB_IMAGE_BASE_URL + logo_art[0]['file_path']
            found_logo = download_image(logo_url, f"{media_id}_logo",is_logo=True)
            if found_logo:
                images['logo'] = found_logo
                images['logo_url'] = logo_url
    
    # Background
    if assets_to_fetch in ['background', 'both']:
        # iso_639_1 is language fields, metadata without it should be textless by default
        background_art = sorted(
            [img for img in data.get('backdrops', []) if img.get('iso_639_1') is None],
            key=lambda x: x.get('vote_average', 0),
            reverse=True
        )
        if background_art:
            background_url = TMDB_IMAGE_BASE_URL + background_art[0]['file_path']
            found_background = download_image(background_url, f"{media_id}_background",is_background=True)
            if found_background:
                images['background'] = found_background
                images['background_url'] = background_url
    
    return images if images else None  
    
def fetch_assets_and_make_screensaver(media_name, category, tmdb_id, tvdb_id):
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
    existing_record = get_record(tmdb_id)

    if existing_record and existing_record['screensaver_location']:
        # Screensaver already made, skip processing
        logging.info(f"{media_name} - Screensaver already exists")
        return

    # Fetch fresh artwork from TMDB first
    artwork_dict = get_tmdb_media_artwork(category, tmdb_id, 'both')
    # TODO - Incorporate fanart as back-up

    if not artwork_dict:
        artwork_dict = {}


    # Verify we have both required assets
    if not artwork_dict.get('logo') or not artwork_dict.get('background'):
        print (artwork_dict)
        logging.error(f"Could not fetch complete artwork for {tmdb_id}")
        return None

    # Create screensaver
    output_filename = f"{OUTPUT_PATH}/{tmdb_id}_screensaver.mp4"
    screensaver = make_screensaver(
        background_path=artwork_dict['background'],
        logo_path=artwork_dict['logo'],
        output_filename=output_filename,
        preview=PREVIEW_MODE
    )
    if screensaver:
        upsert_record(tmdb_id,tvdb_id,media_name,category,artwork_dict['logo_url'],artwork_dict['background_url'],screensaver,True,datetime.now(),datetime.now())

        # Delete local versions of artwork
        logo_local_asset = Path(artwork_dict['logo'])
        background_local_asset = Path(artwork_dict['background'])

        if logo_local_asset.exists() and background_local_asset.exists():
            logo_local_asset.unlink()
            background_local_asset.unlink()
        logging.info(f"{media_name} - Screensaver Created")

def remove_screensaver(tmdb_id:int,scrub_record:bool=False) -> bool:
    """
    Takes a tmdb_id and if a screensaver exists in the defined output location it deletes it and removes location from the db.remove_record.remove_record.
    Args:
        tmdb_id: TheMovieDBId Number
        scrub_record: Fully delete the record from the database
    """
    found_record = get_record(1101383)
    if found_record and found_record['screensaver_location']:
        screensaver_location = Path(found_record['screensaver_location'])
        if screensaver_location.exists:
            screensaver_location.unlink()
    if scrub_record:
        remove_record(tmdb_id)
    else:
        update_record(tmdb_id,screensaver_location=None)
    return True





if __name__ == "__main__":
    # remove_record(1101383)
    remove_screensaver(1101383)
    # fetch_assets_and_make_screensaver('The End Of Oak Street','movie',1101383,1101383)


# for idx, movie in enumerate(unwatched_movies, 1):
#     tmdb_id_str = str(movie['tmdb']) if movie['tmdb'] else None
#     if tmdb_id_str and tmdb_id_str not in generated_ids:
#         fetch_assets_and_make_screensaver(movie['title'], 'movie', tmdb_id_str, movie['tvdb'], idx, total_movies)

#         elapsed = (datetime.now() - start_time).total_seconds()
#         if idx < total_movies:
#             avg_time_per_item = elapsed / idx
#             remaining_items = total_movies - idx
#             estimated_remaining = avg_time_per_item * remaining_items
#             print(f"Elapsed: {int(elapsed // 60)}m - Estimated time to finish: {int(estimated_remaining // 60)} minutes\n")
#     else:
#         print(f"Skipping {movie['title']} (ID: {tmdb_id_str}) - screensaver already generated")

# def process_media():
#     fetch_assets_and_make_screensaver()

