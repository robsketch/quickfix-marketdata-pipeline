FROM python:3.11-bullseye

ARG INDEX_URL

ENV PUB_TABLE=taxi
ENV PYKX_BETA_FEATURES=true
ENV RT_CONFIG=file:///app/config.json
ENV RT_REPLICAS=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-input --no-cache-dir --extra-index-url ${INDEX_URL} -r requirements.txt

COPY config.json .
COPY sample.py .

RUN chown -R nobody:nogroup /app
USER nobody

CMD ["python3", "sample.py"]
