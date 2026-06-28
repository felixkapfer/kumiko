FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KUMIKO_HOST=0.0.0.0 \
    KUMIKO_PORT=8000 \
    KUMIKO_DATA_DIR=/data

WORKDIR /app

RUN useradd --create-home --uid 10001 kumiko \
    && mkdir -p /data \
    && chown -R kumiko:kumiko /data

COPY --chown=kumiko:kumiko . /app

USER kumiko

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import json, urllib.request; json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2))"

CMD ["python", "server.py"]
