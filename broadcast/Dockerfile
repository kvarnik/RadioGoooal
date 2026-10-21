FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn pyyaml
COPY api api
COPY agents agents
COPY *.py ./
COPY data/9000001.json data/9000001.json
COPY data/audio/cache.json data/audio/cache.json

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
