FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ cmake make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir quickfix pykx \
    && pip --no-input install \
       --extra-index-url https://portal.dl.kx.com/assets/pypi/ \
       kxi-rtpy

COPY acceptor/acceptor.py /app/acceptor.py
COPY config/acceptor.cfg  /app/config/acceptor.cfg

RUN mkdir -p /app/logs/store

CMD ["python", "acceptor.py"]
