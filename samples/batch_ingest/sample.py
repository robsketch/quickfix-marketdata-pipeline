import argparse
from datetime import date, datetime, timedelta
import requests
import json
import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pykx as kx
from random import choice, randint, random
import time

class IngestRequestError(Exception):
    def __init__(self, text):
        super().__init__(text)

class IngestError(Exception):
    def __init__(self, text):
        super().__init__(text)

def create_parquet_file(path, num_of_rows, row_group_size):
    print(f'Creating {path} file')

    VENDORS = [
        'Platinum Transport', 'Airport Taxi', 'Midtown',
        'Precision Chauffeur', 'Pocono Daytrips'
    ]
    PAYMENT_TYPES = ['Cash', 'Debit', 'VISA', 'MasterCard', 'AMEX']

    now = datetime.now()
    vendor = [choice(VENDORS) for _ in range(num_of_rows)]
    dist = [random()*num_of_rows for _ in range(num_of_rows)]
    fare = [x*3 for x in dist]
    zero = [0 for _ in range(num_of_rows)]
    tip = [x*0.1 for x in fare]
    total = [x*1.1 for x in fare]
    dropoff = [now + timedelta(minutes=randint(1,20)) for _ in range(num_of_rows)]
    payment_type = [choice(PAYMENT_TYPES) for _ in range(num_of_rows)]

    df = pd.DataFrame({
        'vendor': vendor,
        'pickup': [now for _ in range(num_of_rows)],
        'dropoff': dropoff,
        'passengers': [randint(1,4) for _ in range(num_of_rows)],
        'distance': dist,
        'fare': fare,
        'extra': zero,
        'tax': zero,
        'tip': tip,
        'tolls': zero,
        'fees': zero,
        'total': total,
        'payment_type': payment_type
    })

    table = pa.Table.from_pandas(df)

    pq.write_table(table, path, row_group_size)


def create_db(parquet_file, staging_dir, session_name, row_group):
    print(f'Reading row group {row_group}')
    arrow_table = parquet_file.read_row_group(row_group)

    print('Creating kdb+ table object')
    kx_table = kx.toq(arrow_table)

    kx_table = kx_table.astype({
        'passengers': kx.ShortVector,
        'distance': kx.RealVector,
        'fare': kx.RealVector,
        'extra': kx.RealVector,
        'tax': kx.RealVector,
        'tip': kx.RealVector,
        'tolls': kx.RealVector,
        'fees': kx.RealVector,
        'total': kx.RealVector
    })

    #print(kx_table.dtypes)
    print(f'Number of rows: {kx_table.shape[0].py()}')

    db_path = os.path.join(staging_dir, session_name)

    db = kx.DB(path = db_path)

    print('\nPersisting kdb+ table to disk')
    print(f'Location: {db_path}')
    db.create(kx_table, 'taxi', date.today(), by_field = 'vendor')

    #os.system(f'chmod -R 777 {db_path}')

def send_ingest_request(host, port, session_name, ingest_mode):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    query = {
        'name': session_name,
        'mode': ingest_mode
    }

    print('Sending ingest request to Storage Manager')
    res = requests.post(f'http://{host}:{port}/ingest',
                    headers=headers, data=json.dumps(query))

    if res.status_code != 200:
        raise IngestRequestError(res.text)

    msg = res.json()
    status = msg['status']
    print(f'Batch ingest status: {status}')


def monitor_ingest_status(host, port, session_name):
    print('Monitoring ingestion status...')
    while True:
        res = requests.get(f'http://{host}:{port}/ingest/{session_name}')

        if res.status_code != 200:
            raise IngestRequestError(res.text)

        msg = res.json()
        status = msg['status']
        print(f'Batch ingest status: {status}')

        if status == 'completed':
            return

        if status == 'errored':
            error = msg['error']
            raise IngestError(error)

        time.sleep(1)

def batch_ingest(parquet_file_path, host, port, ingest_mode,
        staging_dir, session_name):
    parquet_file = pq.ParquetFile(parquet_file_path)
    num_row_groups = parquet_file.num_row_groups
    print(f'Number of row groups {num_row_groups}')
    for i in range(num_row_groups):
        create_db(parquet_file, staging_dir, f'{session_name}-{i}', i)
        send_ingest_request(host, port, f'{session_name}-{i}', ingest_mode)
        monitor_ingest_status(host, port, f'{session_name}-{i}')

parser = argparse.ArgumentParser(description='Batch ingest a parquet file')

parser.add_argument('-f', '--file-path', default='/tmp/taxi.parquet',
    help='Parquet file path')

parser.add_argument('-s', '--staging-dir', default='/mnt/db/hdb/staging',
    help='Database staging directory')

parser.add_argument('--host', default='kxi-sm',
    help='Storage Manager container hostname')

parser.add_argument('-p', '--port', default='10001',
    help='Open port on Storage Manager container')

args = parser.parse_args()
print(f'Staging directory: {args.staging_dir}')
print(f'SM hostname: {args.host}')
print(f'SM port: {args.port}')

session_name = 'backfill'
ingest_mode = 'merge'
num_of_rows = 10
row_group_size = 4

create_parquet_file(args.file_path, num_of_rows, row_group_size)

batch_ingest(args.file_path, args.host, args.port, ingest_mode,
    args.staging_dir, session_name)
