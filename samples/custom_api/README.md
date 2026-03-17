# Custom API example

## Introduction

This sample shows how to call a custom API from q. Custom APIs allow you to add new functions to the
databases.

## Installing a custom API

Custom APIs are housed within a folder referred to as a package. The package must contain a
`manifest.json`, which configures the entrypoints for each of the `storage-manager`, `data-access`
and `aggregator` components.

The `config/packages` directory contains a custom API that multiplies a selected column by a
multiplier and returns the original data and a running average of the multiplied column.

See the [kdb Insights documentation](https://code.kx.com/insights/microservices/database/configuration/custom-api.html)
for more details on how custom APIs are installed.

## Calling a custom API
### From q
The `sample.q` scirpt show how to call the custom API from q.
```
q sample.q
```
### HTTP
You can use either a GET request
```
curl "http://localhost:8080/example.daAPI?table=taxi;column=fare;multiplier=10"
```
or POST request.
```
curl -X POST -H 'Content-Type: application/json' http://localhost:8080/example.daAPI -d '{"table":"taxi", "column":"fare", "multiplier":10}'
```
### KXI Python
Ensure you have the latest version of `pip`.
```
pip install --upgrade pip
```
Install the `kxi` package
```
pip install --extra-index-url https://portal.dl.kx.com/assets/pypi/kxi "kxi[all]>=1.14.0"
```
The `sample.py` script shows how to call a custom API using the `kxi` package.
```
python sample.py
```

## Links
* [Installing Custom API (kdb Insights)](https://code.kx.com/insights/microservices/database/configuration/custom-api.html)
* [Use a Custom API (Packaging Quickstart)](https://code.kx.com/insights/enterprise/packaging/quickstart.html#use-a-custom-api)
* [Custom APIs (APIs)](https://code.kx.com/insights/api/database/custom/index.html)
* [Get Data (APIs)](https://code.kx.com/insights/api/database/query/get-data.html)
* [Reference card](https://code.kx.com/q/ref/)
