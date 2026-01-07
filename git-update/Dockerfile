ARG BUILD_FROM=alpine:3.20
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2

RUN apk add --no-cache \
        bash \
        ca-certificates \
        curl \
        jq \
        tzdata \
        python3~=3.12 \
        py3-pip \
        git && \
    python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY rootfs / 

RUN chmod a+x /etc/cont-init.d/*.sh && \
    chmod a+x /etc/services.d/*/run && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

CMD ["/init"]
