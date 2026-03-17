# Publishing data via the kdb Insights Python API

## Introduction

This directory demonstrates how to publish data (via RT) using the [kdb Insights Python API](https://code.kx.com/insights/1.8/api/kxi-python/index.html).

## Running the example

Make sure kdb Insights has been successfully deployed before running this example.

Create a Python virtual environment, e.g.

```
python3 -m venv ~/.venv/my_venv
source ~/.venv/my_venv/bin/activate
```

Update pip:

```
pip install --upgrade pip
```

Install the `kxi` package:

```
pip install --extra-index-url https://portal.dl.kx.com/assets/pypi/kxi "kxi[all]>=1.14.0"
```

Publish a csv file:

```
python sample.py --type csv
```

Publish a parquet file:

```
python sample.py --type parquet
```
