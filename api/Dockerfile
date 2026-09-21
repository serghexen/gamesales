FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# API импортирует настройки локального режима и в обычном серверном запуске.
COPY app.py local_ui_runtime.py ./
COPY domains ./domains
COPY scripts ./scripts
COPY certs ./certs

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["sh", "-lc", "uvicorn app:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}"]
