FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Santiago

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY simulador.py .

CMD ["python", "simulador.py"]
