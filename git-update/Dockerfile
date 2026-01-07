ARG BUILD_FROM=ghcr.io/home-assistant/amd64-addon-base:17.2.0
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apk add --no-cache \
        python3~=3.12 \
        py3-pip \
        git && \
    python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY rootfs / 

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

CMD ["/init"]
