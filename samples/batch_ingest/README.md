
# Batch Ingestion Example

## Introduction
This directory contains an example of batch ingesting an [Apache Parquet](https://parquet.apache.org/) file.
The example combines,
- [PyArrow](https://arrow.apache.org/docs/python/index.html) to generate and read the Parquet file.
- [PyKX](https://code.kx.com/pykx/index.html) is used to convert the Parquet data into a on-disk kdb+ database.
- The [kdb Insights Storage Manager (SM)](https://code.kx.com/insights/microservices/database/storage/index.html) REST API is then used to batch ingest the kdb+ database.

The PyKX database management API is currently in beta phase.

## Running the example

### Pre-requisite
- The InsightsDB must be deployed before the batch ingest example is ran

### Execution
The program will do the following:
1. Generate a `taxi.parquet` file with multiple [row groups](https://parquet.apache.org/docs/concepts/) and store it locally using PyArrow
2. Read the `taxi.parquet` file one row group at a time using PyArrow
3. For each row group batch ingest the data
    1. Create a kdb+ database using the row group data in the HDB staging directory using [PyKX](https://code.kx.com/pykx/2.3/beta-features/db-management.html)
    2. Send a [batch ingestion REST request](https://code.kx.com/insights/microservices/database/storage/batch-ingest.html) to the storage manager (SM)
    3. Monitor the status of the batch ingestion by making REST calls until the status returned is completed

Launch the sample program using Docker Compose:
```
docker compose -f compose-batch-ingest.yaml up
```


## Links
* [Reading and Writing the Apache Parquet Format | arrow.apache.org](https://arrow.apache.org/docs/python/parquet.html)
* [Pandas API - PyKX | code.kx.com](https://code.kx.com/pykx/2.2/user-guide/advanced/Pandas_API.html)
* [Batch ingest - kdb Insights Database | code.kx.com ](https://code.kx.com/insights/1.8/microservices/database/storage/batch-ingest.html)
