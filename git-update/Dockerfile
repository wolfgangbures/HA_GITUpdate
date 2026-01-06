ARG BUILD_FROM=ghcr.io/home-assistant/amd64-addon-base-python:3.12
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY rootfs / 

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

CMD ["/init"]
