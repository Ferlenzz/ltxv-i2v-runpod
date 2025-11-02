# База: готовый ComfyUI+LTX-Video (I2V) образ
FROM camenduru/ltx-video-i2v-comfyui:fp16

# Утилиты и Python-зависимости
USER root
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl jq && rm -rf /var/lib/apt/lists/*

# В отдельный слой — pip-пакеты для сервера/RunPod
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Наши скрипты
WORKDIR /app
COPY app/ /app
RUN chmod +x /app/start.sh

# Порты:
#  - 8188 — ComfyUI (из базового образа)
#  - 8000 — наш healthcheck (опц.)
EXPOSE 8000 8188

# ENV:
#  WARMUP=1 — прогрев при старте (компиляция графа, загрузка весов)
#  SAVE_DIR=/workspace/outputs — куда складывать видео/кадры
#  CACHE_DIR=/workspace/cache — для last_image
ENV WARMUP=1 \
    SAVE_DIR=/workspace/outputs \
    CACHE_DIR=/workspace/cache \
    COMFY_HOST=127.0.0.1 \
    COMFY_PORT=8188

# Создадим каталоги для артефактов
RUN mkdir -p $SAVE_DIR $CACHE_DIR

# Стартуем ComfyUI в фоне + наш RunPod handler
CMD ["/bin/bash", "-lc", "/app/start.sh"]
