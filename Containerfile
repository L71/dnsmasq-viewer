FROM python:3.14-slim

WORKDIR /app

COPY src/server.py ./src/server.py
COPY public/ ./public/

RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/status')" || exit 1

CMD ["python", "src/server.py"]
