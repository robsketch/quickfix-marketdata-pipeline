# kdb Insight Python API

# Introduction

This directory contains examples of querying InsightsDB using the [kdb Insights Python API](https://code.kx.com/insights/api/kxi-python/index.html).

### Pre-requisite

- The InsightsDB has been deployed
- The `taxi` table contains recent data
  - If this is not the case run one of the publishing samples

## Running the example

Python packages should typically be installed in a virtual environment. This can be done with the [`venv`](https://docs.python.org/3/library/venv.html)
package from the standard library, e.g.

```
python3 -m venv ~/.venv/my_venv
source ~/.venv/my_venv/bin/activate
```

To install the kdb Insights Python API ensure you have a recent version of pip installed:

```
pip install --upgrade pip
```

Now install the `kxi` library with the following command:

```
pip --no-input install --extra-index-url https://portal.dl.kx.com/assets/pypi kxi
```

Run the example with this command

```
python3 sample.py
```

The example program illustrates the following:

1. A [getMeta API](https://code.kx.com/insights/api/kxi-python/query.html#get_meta) call
2. A [SQL API](https://code.kx.com/insights/api/kxi-python/query.html#sql) call
3. A [getData API](https://code.kx.com/insights/api/kxi-python/query.html#get_data) call

Please note, to allow SQL API calls the `KXI_ALLOWED_SBX_APIS` environment variable must be set on the DAP and RC containers. This has already been done in the provided `compose.yml` and `.env` files. See the [query configuration documentation](https://code.kx.com/insights/enterprise/database/configuration/assembly/query.html#environment-variables) for more details.
