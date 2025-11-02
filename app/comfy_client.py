import os
import time
import json
import base64
import requests
from typing import Optional, Tuple

COMFY_URL = f"http://{os.environ.get('COMFY_HOST','127.0.0.1')}:{os.environ.get('COMFY_PORT','8188')}"

def _wait_history(pid: str, timeout_s: int = 900) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = requests.get(f"{COMFY_URL}/history/{pid}")
        if r.status_code == 200 and r.json():
            hist = r.json()
            if pid in hist:
                return hist[pid]
        time.sleep(1.0)
    raise TimeoutError("ComfyUI history wait timeout")

def _download_output(hist: dict, save_dir: str) -> Tuple[str, str]:
    """Вытащим mp4 путь и первый кадр (или последний)"""
    # ComfyUI кладёт файлы в /output; но базовый образ обычно монтирует в /opt/ComfyUI/output
    # у camenduru — /workspace/ComfyUI/output; на всякий случай найдём из history
    video_path = None
    image_path = None
    for node_id, node_val in hist.get("outputs", {}).items():
        for item in node_val.get("images", []):
            # изображения (кадры) — возьмём последний кадр
            image_path = item.get("filename") or image_path
        for item in node_val.get("videos", []):
            video_path = item.get("filename") or video_path

    if not video_path:
        # некоторые воркфлоу пишут как изображения-последовательность; соберём через ffmpeg
        # (опционально — но лучше иметь запасной план)
        pass

    return video_path, image_path

def load_workflow(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

def submit_workflow(wf: dict) -> str:
    r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": wf})
    r.raise_for_status()
    return r.json()["prompt_id"]

def encode_image_from_path(path: str) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

def save_last_image(source_path: Optional[str], cache_dir: str) -> Optional[str]:
    if not source_path:
        return None
    os.makedirs(cache_dir, exist_ok=True)
    dst = os.path.join(cache_dir, "last.png")
    try:
        # просто скопируем
        import shutil
        shutil.copy2(source_path, dst)
        return dst
    except Exception:
        return None
