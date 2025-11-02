import os, json, time
import runpod
import requests
from typing import Any, Dict
from comfy_client import load_workflow, submit_workflow, _wait_history, _download_output, save_last_image
from utils import fetch_image_to_base64, extract_last_frame_from_video

WF_PATH = "/app/workflows/ltxv_i2v_api.json"
SAVE_DIR = os.environ.get("SAVE_DIR","/workspace/outputs")
CACHE_DIR = os.environ.get("CACHE_DIR","/workspace/cache")
COMFY_URL = f"http://{os.environ.get('COMFY_HOST','127.0.0.1')}:{os.environ.get('COMFY_PORT','8188')}"

os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

def build_workflow(inp: Dict[str, Any]) -> dict:
    wf = load_workflow(WF_PATH)

    # входная картинка
    image_b64 = None
    if inp.get("use_last_image"):
        last = os.path.join(CACHE_DIR, "last.png")
        if os.path.exists(last):
            with open(last, "rb") as f:
                import base64
                image_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

    if not image_b64:
        image_b64 = fetch_image_to_base64(inp["image"])

    # подстановка параметров
    prompt = inp.get("prompt", "")
    negative = inp.get("negative_prompt", "")
    num_frames = int(inp.get("num_frames", 96))
    fps = int(inp.get("fps", 24))
    seed = int(inp.get("seed", 0))

    # узел 1 — картинка
    wf["1"]["inputs"]["image"] = image_b64
    # узел 2 — параметры LTXV
    wf["2"]["inputs"]["text"] = prompt
    wf["2"]["inputs"]["negative"] = negative
    wf["2"]["inputs"]["num_frames"] = num_frames
    wf["2"]["inputs"]["fps"] = fps
    wf["2"]["inputs"]["seed"] = seed
    # узел 3 — видео сейвера
    wf["3"]["inputs"]["fps"] = fps

    return wf

def handler(event):
    """RunPod event: {input: {...}}"""
    try:
        inp = event.get("input", {})
        assert ("image" in inp) or inp.get("use_last_image"), "Provide 'image' (URL/path/base64) or set use_last_image=true"

        wf = build_workflow(inp)
        pid = submit_workflow(wf)
        hist = _wait_history(pid, timeout_s=int(inp.get("timeout", 900)))
        video_path, image_path = _download_output(hist, SAVE_DIR)

        # сохраним last image (если есть кадры); иначе вытащим из видео последний кадр
        last_png = None
        if image_path and os.path.exists(image_path):
            last_png = save_last_image(image_path, CACHE_DIR)
        elif video_path and os.path.exists(video_path):
            last_png = extract_last_frame_from_video(video_path, os.path.join(CACHE_DIR, "last.png"))

        # формируем ответ
        result = {
            "video_path": video_path,
            "last_image_path": last_png,
            "frames": hist.get("outputs", {}),
            "pid": pid
        }
        return {"status": "ok", "output": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

runpod.serverless.start({"handler": handler})
