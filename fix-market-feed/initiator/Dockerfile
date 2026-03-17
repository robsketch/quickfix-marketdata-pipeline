FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ cmake make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir quickfix

COPY initiator/initiator.py /app/initiator.py
COPY config/initiator.cfg   /app/config/initiator.cfg

RUN mkdir -p /app/logs/store

CMD ["python", "initiator.py"]
