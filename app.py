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
    background = Image.open(background_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    # Calculate position for bottom-left placement with a margin
    x = margin
    y = background.height - logo.height - margin

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
    background = Image.open(background_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    bg_w, bg_h = background.size
    logo_w, logo_h = logo.size

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
        y = bg_h - logo_h - margin
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
    


