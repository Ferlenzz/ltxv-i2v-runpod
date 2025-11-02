import os, re, base64, io, requests
from PIL import Image

def is_data_url(s: str) -> bool:
    return isinstance(s, str) and s.startswith("data:image")

def fetch_image_to_base64(url_or_b64: str) -> str:
    if is_data_url(url_or_b64):
        return url_or_b64
    if url_or_b64.startswith("http"):
        r = requests.get(url_or_b64, timeout=30)
        r.raise_for_status()
        b = r.content
    else:
        with open(url_or_b64, "rb") as f:
            b = f.read()
    return "data:image/png;base64," + base64.b64encode(b).decode("utf-8")

def extract_last_frame_from_video(video_path: str, out_path: str) -> str:
    os.system(f'ffmpeg -y -i "{video_path}" -vf "select=eq(n\\,last_n)" -frames:v 1 "{out_path}"')
    return out_path
