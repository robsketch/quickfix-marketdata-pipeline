FROM python:3.11-bullseye

ENV PYKX_UNLICENSED=true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY query.py .

RUN chown -R nobody:nogroup /app
USER nobody

CMD ["python3", "query.py"]
