#!/usr/bin/env bash
set -e

# 1) запускаем ComfyUI headless (он уже установлен в базовом образе)
# базовый образ слушает 8188; поднимем в фоне
echo "[start] launching ComfyUI on ${COMFY_HOST}:${COMFY_PORT} ..."
python /opt/ComfyUI/main.py --listen 0.0.0.0 --port ${COMFY_PORT} --disable-auto-launch &

# ждём, пока сервер поднимется
echo "[start] waiting ComfyUI..."
for i in {1..60}; do
  if curl -sf http://${COMFY_HOST}:${COMFY_PORT}/system_stats > /dev/null; then
    echo "[start] ComfyUI is up."
    break
  fi
  sleep 2
done

# 2) прогрев (по желанию)
if [ "${WARMUP}" = "1" ]; then
  echo "[start] warmup..."
  python -u - <<'PY'
import os, time
import requests, json
host = os.environ.get("COMFY_HOST","127.0.0.1")
port = os.environ.get("COMFY_PORT","8188")
url  = f"http://{host}:{port}"
# минимальный прогрев: загрузить граф, не генерируя длинный клип
wf = json.load(open("/app/workflows/ltxv_i2v_api.json","r"))
# заглушка вместо картинки: ComfyUI примет и создаст короткую последовательность
# сократим до 14 кадров для быстрого компиля
for n in wf.values():
    if isinstance(n, dict) and "inputs" in n and "num_frames" in n["inputs"]:
        n["inputs"]["num_frames"] = 14
        n["inputs"]["fps"] = 6
# отправим граф
r = requests.post(f"{url}/prompt", json={"prompt": wf})
r.raise_for_status()
print("[warmup] graph submitted:", r.json().get("prompt_id"))
PY
  echo "[start] warmup submitted."
fi

# 3) запускаем RunPod handler (	Serverless)
echo "[start] starting runpod handler..."
python /app/handler.py
