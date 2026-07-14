import requests
import os
from dotenv import load_dotenv
import random
from PIL import Image
import numpy as np
from moviepy import VideoClip
import math



load_dotenv()

FANARTTV_API_KEY = os.environ["FANARTTV_API_KEY"]



def download_image(image_url,filename,save_dir="artwork"):
    file_extension = image_url.split('.')[-1]
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{filename}.{file_extension}")
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    else:
        return False
    


def get_media_artwork(media_type, media_id):
    url = f"https://webservice.fanart.tv/v3.2/{media_type}/{media_id}"
    params = {"api_key": FANARTTV_API_KEY}

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(response.status_code, response.text)
        raise SystemExit()

    data = response.json()

    logo_art = [image for image in data.get('hdtvlogo', []) if image['lang'] == 'en']
    background_art = data.get('showbackground', [])


    if logo_art and background_art:
        logo=logo_art[0]
        background = random.choice(background_art)

    
        

        logo_save_sucess = download_image(logo['url'],f"{media_id}_logo")
        background_save_sucess = download_image(background['url'],f"{media_id}_background")
        return logo_save_sucess and background_save_sucess
    else:
        return False
                    

    
def combine_images(background_path, logo_path, output_filename, margin=20):
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
    fps=30,
    zoom_end=1.03,       # subtle background zoom
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
            Image.AFFINE,
            (a, 0, src_left, 0, d, src_top),
            resample=Image.BICUBIC
        )

        frame = cropped_bg.copy()

        # --- Logo drift: simple integer positioning, no sub-pixel needed ---
        x = margin + round(logo_drift_px * progress)
        y = bg_h - logo_h - margin
        frame.paste(logo, (x, y), logo)

        return np.array(frame.convert("RGB"))

    clip = VideoClip(make_frame, duration=duration).with_fps(fps)

    clip.write_videofile(
        output_filename,
        codec="libx264",
        fps=fps,
        audio=False,
        ffmpeg_params=["-crf", "18"]
    )

media_id=454109
get_media_artwork('tv',media_id)
make_screensaver(f'./artwork/{media_id}_background.jpg',f'./artwork/{media_id}_logo.png',f'{media_id}_image.mkv',6)
# combine_images('./artwork/403245_background.jpg','./artwork/403245_logo.png','71663_image.png')
# make_screensaver('./artwork/71663_background.jpg','./artwork/71663_logo.png','71663_image.mkv',6)