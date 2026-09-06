FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-api.txt ./requirements-api.txt

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-api.txt

COPY api ./api
COPY rag ./rag
COPY entrypoint.sh ./entrypoint.sh

RUN mkdir -p analytics models monitoring reports && \
    useradd --create-home --shell /bin/sh appuser && \
    chown -R appuser:appuser /app && \
    chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
